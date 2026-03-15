"""
InteriMatch AI - Routes Upload & Parsing CV
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Candidate, Resume, ExtractedProfile
from app.schemas.schemas import CVUploadResponse, ExtractedProfileResponse
from app.services.cv_parser import parse_cv

settings = get_settings()
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


@router.post("/upload", response_model=CVUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
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
    file_path = Path(settings.upload_dir) / safe_name
    file_path.write_bytes(file_bytes)

    # Parsing du CV via IA
    try:
        parsed = await parse_cv(file_bytes, file.filename)
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
        created_by=uuid.UUID(user["sub"]),
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
