"""
InteriMatch AI - Dépendances partagées (auth, autorisation, anti-IDOR).
"""

import uuid as _uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_access_token, oauth2_scheme
from app.models.models import (
    BulkUploadJob,
    Candidate,
    GeneratedEmail,
    MatchingResult,
    Resume,
    User,
)


async def get_current_user_db(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")
    try:
        uid = _uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Token invalide")
    result = await db.execute(
        select(User).options(selectinload(User.settings)).where(User.id == uid)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    return user


# ---------------------------------------------------------------------------
# Helpers d'autorisation (anti-IDOR / élévation horizontale)
# ---------------------------------------------------------------------------
# Toutes les ressources métier (Candidate, Resume, MatchingResult, GeneratedEmail)
# remontent à un Candidate.created_by. Ces helpers DOIVENT être utilisés sur
# chaque endpoint qui accepte un identifiant de ressource utilisateur.
# Ils renvoient 404 (et non 403) pour éviter de divulguer l'existence
# d'une ressource appartenant à un autre utilisateur.

_NOT_FOUND = HTTPException(status_code=404, detail="Ressource introuvable")


async def get_owned_candidate(
    candidate_id: _uuid.UUID,
    db: AsyncSession,
    user: User,
    *,
    with_resumes: bool = False,
) -> Candidate:
    """Renvoie un Candidate uniquement s'il appartient à l'utilisateur courant."""
    stmt = select(Candidate).where(
        Candidate.id == candidate_id,
        Candidate.created_by == user.id,
    )
    if with_resumes:
        stmt = stmt.options(
            selectinload(Candidate.resumes).selectinload(Resume.extracted_profile)
        )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise _NOT_FOUND
    return candidate


async def get_owned_resume(
    resume_id: _uuid.UUID,
    db: AsyncSession,
    user: User,
) -> Resume:
    """Renvoie un Resume uniquement si son Candidate appartient à l'utilisateur."""
    stmt = (
        select(Resume)
        .join(Candidate, Resume.candidate_id == Candidate.id)
        .where(Resume.id == resume_id, Candidate.created_by == user.id)
        .options(selectinload(Resume.extracted_profile))
    )
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()
    if not resume:
        raise _NOT_FOUND
    return resume


async def get_owned_matching(
    matching_id: _uuid.UUID,
    db: AsyncSession,
    user: User,
    *,
    with_offer: bool = False,
) -> MatchingResult:
    """Renvoie un MatchingResult uniquement si le candidat appartient à l'utilisateur."""
    stmt = (
        select(MatchingResult)
        .join(Candidate, MatchingResult.candidate_id == Candidate.id)
        .where(MatchingResult.id == matching_id, Candidate.created_by == user.id)
    )
    if with_offer:
        stmt = stmt.options(selectinload(MatchingResult.job_offer))
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()
    if not match:
        raise _NOT_FOUND
    return match


async def get_owned_email(
    email_id: _uuid.UUID,
    db: AsyncSession,
    user: User,
) -> GeneratedEmail:
    """Renvoie un GeneratedEmail uniquement si le matching appartient à l'utilisateur."""
    stmt = (
        select(GeneratedEmail)
        .join(MatchingResult, GeneratedEmail.matching_result_id == MatchingResult.id)
        .join(Candidate, MatchingResult.candidate_id == Candidate.id)
        .where(GeneratedEmail.id == email_id, Candidate.created_by == user.id)
    )
    result = await db.execute(stmt)
    email = result.scalar_one_or_none()
    if not email:
        raise _NOT_FOUND
    return email


async def get_owned_bulk_job(
    job_id: _uuid.UUID,
    db: AsyncSession,
    user: User,
) -> BulkUploadJob:
    """Renvoie un BulkUploadJob uniquement s'il appartient à l'utilisateur."""
    stmt = select(BulkUploadJob).where(
        BulkUploadJob.id == job_id,
        BulkUploadJob.user_id == user.id,
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise _NOT_FOUND
    return job
