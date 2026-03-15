"""
InteriMatch AI - Routes Génération & Gestion d'emails
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    MatchingResult,
    GeneratedEmail,
    Candidate,
    Resume,
    ExtractedProfile,
    JobOffer,
)
from app.schemas.schemas import (
    GeneratedEmailResponse,
    EmailGenerateRequest,
    EmailUpdateRequest,
)
from app.services.email_generator import generate_candidate_email

router = APIRouter()


@router.post("/generate", response_model=GeneratedEmailResponse, status_code=201)
async def generate_email(
    request: EmailGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Génère un email professionnel pour une correspondance candidat/offre.
    """
    # Récupérer le matching avec les relations
    result = await db.execute(
        select(MatchingResult)
        .options(selectinload(MatchingResult.job_offer))
        .where(MatchingResult.id == request.matching_result_id)
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Résultat de matching introuvable")

    # Récupérer le profil du candidat
    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.resumes).selectinload(Resume.extracted_profile))
        .where(Candidate.id == match.candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate or not candidate.resumes:
        raise HTTPException(status_code=400, detail="Candidat ou CV introuvable")

    latest_resume = sorted(candidate.resumes, key=lambda r: r.imported_at, reverse=True)[0]
    profile = latest_resume.extracted_profile
    if not profile:
        raise HTTPException(status_code=400, detail="Profil extrait introuvable")

    # Préparer les données
    profile_dict = {
        "skills": profile.skills or [],
        "experiences": profile.experiences or [],
        "education": profile.education or [],
        "profile_summary": profile.profile_summary,
        "years_of_experience": profile.years_of_experience,
    }
    candidate_dict = {
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "location": candidate.location,
        "availability": candidate.availability,
    }
    offer_dict = {
        "title": match.job_offer.title,
        "company_name": match.job_offer.company_name,
        "location": match.job_offer.location,
        "description": match.job_offer.description or "",
    }

    # Générer le mail via IA
    email_data = await generate_candidate_email(
        profile=profile_dict,
        candidate=candidate_dict,
        offer=offer_dict,
        match_score=match.global_score,
        match_explanation=match.explanation or "",
    )

    # Sauvegarder
    generated_email = GeneratedEmail(
        matching_result_id=match.id,
        subject=email_data["subject"],
        body=email_data["body"],
        status="draft",
    )
    db.add(generated_email)
    await db.flush()
    await db.refresh(generated_email)
    return generated_email


@router.get("/{email_id}", response_model=GeneratedEmailResponse)
async def get_email(
    email_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Récupère un email généré."""
    result = await db.execute(select(GeneratedEmail).where(GeneratedEmail.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email introuvable")
    return email


@router.put("/{email_id}", response_model=GeneratedEmailResponse)
async def update_email(
    email_id: uuid.UUID,
    data: EmailUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Mettre à jour un email (édition manuelle, validation)."""
    result = await db.execute(select(GeneratedEmail).where(GeneratedEmail.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email introuvable")

    if data.subject is not None:
        email.subject = data.subject
    if data.body is not None:
        email.body = data.body
    if data.status is not None:
        email.status = data.status
        if data.status == "validated":
            email.validated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(email)
    return email
