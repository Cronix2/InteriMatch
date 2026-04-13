"""
InteriMatch AI - Service de déduplication des candidats
Détecte les doublons par nom, reconnaissance faciale et similarité de parcours.
"""

import io
import logging
import re
import uuid
from difflib import SequenceMatcher

import pdfplumber
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Candidate, Resume, ExtractedProfile

logger = logging.getLogger(__name__)

# Try importing face_recognition — it's optional
try:
    import face_recognition
    import numpy as np
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.info("face_recognition non installé — la dédup faciale sera désactivée")

FACE_DISTANCE_THRESHOLD = 0.5  # Lower = stricter match
NAME_SIMILARITY_THRESHOLD = 0.85
CAREER_SIMILARITY_THRESHOLD = 0.6


def _normalize_name(name: str | None) -> str:
    """Normalise un nom pour comparaison."""
    if not name:
        return ""
    return re.sub(r"[^a-z\u00e0-\u00ff]", "", name.strip().lower())


def _name_similarity(first1: str, last1: str, first2: str, last2: str) -> float:
    """Score de similarité entre deux noms (0-1)."""
    f1, l1 = _normalize_name(first1), _normalize_name(last1)
    f2, l2 = _normalize_name(first2), _normalize_name(last2)
    if not (f1 and l1 and f2 and l2):
        return 0.0
    # Exact match
    if f1 == f2 and l1 == l2:
        return 1.0
    # Swapped first/last
    if f1 == l2 and l1 == f2:
        return 0.95
    # Fuzzy match
    score_direct = (
        SequenceMatcher(None, f1, f2).ratio() +
        SequenceMatcher(None, l1, l2).ratio()
    ) / 2
    score_swapped = (
        SequenceMatcher(None, f1, l2).ratio() +
        SequenceMatcher(None, l1, f2).ratio()
    ) / 2
    return max(score_direct, score_swapped)


def _career_similarity(profile1: dict, profile2: ExtractedProfile) -> float:
    """Compare career paths using skills + job titles + experiences."""
    scores = []

    # Skills overlap
    skills1 = set(s.lower() for s in (profile1.get("skills") or []))
    skills2 = set(s.lower() for s in (profile2.skills or []))
    if skills1 and skills2:
        overlap = len(skills1 & skills2) / max(len(skills1 | skills2), 1)
        scores.append(overlap)

    # Job titles overlap
    titles1 = set(t.lower() for t in (profile1.get("desired_job_titles") or []))
    titles2 = set(t.lower() for t in (profile2.desired_job_titles or []))
    if titles1 and titles2:
        overlap = len(titles1 & titles2) / max(len(titles1 | titles2), 1)
        scores.append(overlap)

    # Experience companies
    companies1 = set()
    for exp in (profile1.get("experiences") or []):
        if exp.get("company"):
            companies1.add(exp["company"].lower().strip())
    companies2 = set()
    for exp in (profile2.experiences or []):
        if isinstance(exp, dict) and exp.get("company"):
            companies2.add(exp["company"].lower().strip())
    if companies1 and companies2:
        overlap = len(companies1 & companies2) / max(len(companies1 | companies2), 1)
        scores.append(overlap)

    # Professional domain
    dom1 = (profile1.get("professional_domain") or "").lower().strip()
    dom2 = (profile2.professional_domain or "").lower().strip()
    if dom1 and dom2:
        scores.append(SequenceMatcher(None, dom1, dom2).ratio())

    return sum(scores) / max(len(scores), 1)


def extract_face_encoding_from_pdf(file_bytes: bytes) -> list[float] | None:
    """Extract a face encoding from the first photo found in a PDF."""
    if not FACE_RECOGNITION_AVAILABLE:
        return None
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                for img_meta in (page.images or []):
                    try:
                        pil_img = page.to_image(resolution=150).original
                        img_array = np.array(pil_img)
                        encodings = face_recognition.face_encodings(img_array)
                        if encodings:
                            return encodings[0].tolist()
                    except Exception:
                        continue
    except Exception as e:
        logger.debug("Face extraction failed: %s", e)
    return None


def _face_matches(encoding1: list[float] | None, encoding2: list[float] | None) -> bool:
    """Check if two face encodings match."""
    if not FACE_RECOGNITION_AVAILABLE or not encoding1 or not encoding2:
        return False
    try:
        import numpy as np
        e1 = np.array(encoding1)
        e2 = np.array(encoding2)
        distance = np.linalg.norm(e1 - e2)
        return distance < FACE_DISTANCE_THRESHOLD
    except Exception:
        return False


async def find_duplicate(
    db: AsyncSession,
    user_id: uuid.UUID,
    new_profile: dict,
    first_name: str,
    last_name: str,
    face_encoding: list[float] | None = None,
) -> dict | None:
    """
    Check if a candidate already exists for this user.
    Returns {candidate, match_type, similarity} or None.
    """
    # Load existing candidates with their profiles
    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.resumes).selectinload(Resume.extracted_profile))
        .where(Candidate.created_by == user_id)
    )
    existing = result.scalars().unique().all()

    best_match = None
    best_score = 0.0

    for candidate in existing:
        match_reasons = []
        combined_score = 0.0

        # Name similarity
        name_sim = _name_similarity(first_name, last_name, candidate.first_name, candidate.last_name)
        if name_sim >= NAME_SIMILARITY_THRESHOLD:
            match_reasons.append("name")
            combined_score += name_sim * 0.4

        # Face matching
        if face_encoding and candidate.face_encoding:
            if _face_matches(face_encoding, candidate.face_encoding):
                match_reasons.append("face")
                combined_score += 0.35

        # Career similarity (only if name matches to avoid expensive comparison)
        if name_sim >= 0.5 and candidate.resumes:
            latest = sorted(candidate.resumes, key=lambda r: r.imported_at, reverse=True)[0]
            if latest.extracted_profile:
                career_sim = _career_similarity(new_profile, latest.extracted_profile)
                if career_sim >= CAREER_SIMILARITY_THRESHOLD:
                    match_reasons.append("career")
                    combined_score += career_sim * 0.25

        if match_reasons and combined_score > best_score:
            best_score = combined_score
            best_match = {
                "candidate_id": str(candidate.id),
                "candidate_name": f"{candidate.first_name} {candidate.last_name}",
                "match_reasons": match_reasons,
                "similarity": round(combined_score, 2),
                "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            }

    # Only return if score is meaningful (at least name match)
    if best_match and best_score >= 0.3:
        return best_match
    return None
