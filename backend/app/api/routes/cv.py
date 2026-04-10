"""
InteriMatch AI - Routes Upload & Parsing CV
"""

import io
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Candidate, Resume, ExtractedProfile, User
from app.schemas.schemas import CVUploadResponse, ExtractedProfileResponse
from app.services.cv_parser import parse_cv
from app.api.deps import get_current_user_db

from fpdf import FPDF

settings = get_settings()
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


@router.post("/upload", response_model=CVUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """
    Upload un CV, extrait le texte, analyse via IA, crée le candidat et le profil.
    """
    # Validation du fichier
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté ({suffix}). Formats acceptés : {', '.join(ALLOWED_EXTENSIONS)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10 Mo)")

    # Sauvegarde du fichier
    file_id = uuid.uuid4()
    safe_name = f"{file_id}{suffix}"
    file_path = Path(settings.upload_dir).resolve() / safe_name
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(file_bytes)

    # Parsing du CV via IA
    try:
        parsed = await parse_cv(file_bytes, file.filename, user_id=str(user.id), user_settings=user.settings)
    except ValueError as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse du CV : {str(e)}")

    profile_data = parsed["profile"]

    # Création du candidat
    candidate = Candidate(
        first_name=profile_data.get("first_name", ""),
        last_name=profile_data.get("last_name", ""),
        email=profile_data.get("email"),
        phone=profile_data.get("phone"),
        location=profile_data.get("location"),
        availability=profile_data.get("availability"),
        processing_status="pending",
        created_by=user.id,
    )
    db.add(candidate)
    await db.flush()

    # Création du CV
    resume = Resume(
        candidate_id=candidate.id,
        file_name=file.filename,
        file_type=suffix.lstrip("."),
        file_path=str(file_path),
        raw_text=parsed["raw_text"],
    )
    db.add(resume)
    await db.flush()

    # Création du profil extrait
    extracted_profile = ExtractedProfile(
        resume_id=resume.id,
        skills=profile_data.get("skills", []),
        experiences=profile_data.get("experiences", []),
        education=profile_data.get("education", []),
        certifications=profile_data.get("certifications", []),
        languages=profile_data.get("languages", []),
        mobility=profile_data.get("mobility"),
        profile_summary=profile_data.get("profile_summary"),
        years_of_experience=profile_data.get("years_of_experience"),
        desired_job_titles=profile_data.get("desired_job_titles", []),
        professional_domain=profile_data.get("professional_domain"),
    )
    db.add(extracted_profile)
    await db.flush()
    await db.refresh(candidate)
    await db.refresh(resume)
    await db.refresh(extracted_profile)

    return CVUploadResponse(
        resume=resume,
        candidate=candidate,
        extracted_profile=extracted_profile,
    )


@router.get("/profile/{resume_id}", response_model=ExtractedProfileResponse)
async def get_extracted_profile(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Récupère le profil extrait d'un CV."""
    result = await db.execute(
        select(ExtractedProfile).where(ExtractedProfile.resume_id == resume_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil extrait introuvable")
    return profile


@router.get("/candidate/{candidate_id}/profile")
async def get_candidate_profile(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Récupère le profil extrait + infos candidat pour un candidat donné."""
    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.resumes).selectinload(Resume.extracted_profile))
        .where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate or not candidate.resumes:
        raise HTTPException(status_code=404, detail="Candidat ou CV introuvable")

    latest_resume = sorted(candidate.resumes, key=lambda r: r.imported_at, reverse=True)[0]
    profile = latest_resume.extracted_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profil extrait introuvable")

    return {
        "candidate": {
            "id": str(candidate.id),
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "location": candidate.location,
        },
        "extracted_profile": {
            "skills": profile.skills or [],
            "experiences": profile.experiences or [],
            "education": profile.education or [],
            "certifications": profile.certifications or [],
            "languages": profile.languages or [],
            "mobility": profile.mobility,
            "profile_summary": profile.profile_summary,
            "years_of_experience": profile.years_of_experience,
            "desired_job_titles": profile.desired_job_titles or [],
            "professional_domain": profile.professional_domain,
        },
    }


@router.get("/candidate/{candidate_id}/anonymized-cv")
async def get_anonymized_cv(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Génère un CV anonymisé en PDF à partir des données extraites (sans nom, email, téléphone, photo)."""
    

    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.resumes).selectinload(Resume.extracted_profile))
        .where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate or not candidate.resumes:
        raise HTTPException(status_code=404, detail="Candidat ou CV introuvable")

    latest_resume = sorted(candidate.resumes, key=lambda r: r.imported_at, reverse=True)[0]
    profile = latest_resume.extracted_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profil extrait introuvable")

    def safe(text: str | None) -> str:
        """Encode text to latin-1 safe string for fpdf2 built-in fonts."""
        if not text:
            return ""
        return text.encode("latin-1", "replace").decode("latin-1")

    # Generate anonymized PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "CV Anonyme", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    # Domain / titles
    if profile.professional_domain or profile.desired_job_titles:
        pdf.set_font("Helvetica", "I", 12)
        domain = safe(profile.professional_domain)
        titles = safe(", ".join(profile.desired_job_titles or []))
        header = domain if domain else titles
        pdf.cell(0, 8, header, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(2)

    # Mobility
    if profile.mobility:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, safe(f"Zone de mobilit\u00e9 : {profile.mobility}"), new_x="LMARGIN", new_y="NEXT", align="C")

    # Years of experience
    if profile.years_of_experience:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, safe(f"{profile.years_of_experience} an(s) d'exp\u00e9rience"), new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(6)

    def section_title(title: str):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 9, safe(f"  {title}"), new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(3)

    # Profile summary
    if profile.profile_summary:
        section_title("Profil")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, safe(profile.profile_summary))
        pdf.ln(4)

    # Skills
    if profile.skills:
        section_title("Comp\u00e9tences")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, safe(", ".join(profile.skills)))
        pdf.ln(4)

    # Experiences
    if profile.experiences:
        section_title("Exp\u00e9riences professionnelles")
        for exp in profile.experiences:
            pdf.set_font("Helvetica", "B", 10)
            title_text = safe(exp.get("title", ""))
            company = safe(exp.get("company", ""))
            duration = safe(exp.get("duration", ""))
            pdf.cell(0, 6, f"{title_text} - {company}", new_x="LMARGIN", new_y="NEXT")
            if duration:
                pdf.set_font("Helvetica", "I", 9)
                pdf.cell(0, 5, duration, new_x="LMARGIN", new_y="NEXT")
            desc = safe(exp.get("description", ""))
            if desc:
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, desc)
            pdf.ln(2)
        pdf.ln(2)

    # Education
    if profile.education:
        section_title("Formation")
        for edu in profile.education:
            pdf.set_font("Helvetica", "B", 10)
            diploma = safe(edu.get("diploma", ""))
            school = safe(edu.get("school", ""))
            year = safe(str(edu.get("year", "")))
            pdf.cell(0, 6, f"{diploma} - {school}", new_x="LMARGIN", new_y="NEXT")
            if year:
                pdf.set_font("Helvetica", "I", 9)
                pdf.cell(0, 5, year, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        pdf.ln(2)

    # Certifications
    if profile.certifications:
        section_title("Certifications")
        pdf.set_font("Helvetica", "", 10)
        for cert in profile.certifications:
            pdf.cell(0, 6, safe(f"- {cert}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Languages
    if profile.languages:
        section_title("Langues")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, safe(", ".join(profile.languages)), new_x="LMARGIN", new_y="NEXT")

    # Output
    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cv_anonymise.pdf"},
    )
