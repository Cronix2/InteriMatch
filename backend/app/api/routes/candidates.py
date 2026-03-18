"""
InteriMatch AI - Routes Candidats
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Candidate, Resume, ExtractedProfile
from app.schemas.schemas import CandidateCreate, CandidateResponse

router = APIRouter()


@router.get("/pipeline")
async def list_pipeline_candidates(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Liste les candidats avec statut de traitement pour le pipeline."""
    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.resumes).selectinload(Resume.extracted_profile))
        .where(Candidate.created_by == uuid.UUID(user["sub"]))
        .order_by(Candidate.created_at.desc())
    )
    candidates = result.scalars().unique().all()

    pipeline = []
    for c in candidates:
        profile_data = {}
        if c.resumes:
            latest = sorted(c.resumes, key=lambda r: r.imported_at, reverse=True)[0]
            if latest.extracted_profile:
                p = latest.extracted_profile
                profile_data = {
                    "professional_domain": p.professional_domain,
                    "desired_job_titles": p.desired_job_titles or [],
                    "mobility": p.mobility,
                    "skills": (p.skills or [])[:5],
                }
        pipeline.append({
            "id": str(c.id),
            "first_name": c.first_name,
            "last_name": c.last_name,
            "email": c.email,
            "location": c.location,
            "processing_status": c.processing_status or "pending",
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "profile": profile_data,
        })
    return pipeline


@router.put("/{candidate_id}/processing-status")
async def update_processing_status(
    candidate_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Met à jour le statut de traitement d'un candidat."""
    new_status = body.get("status")
    if new_status not in ("pending", "matching", "email", "completed"):
        raise HTTPException(status_code=400, detail="Statut invalide")
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidat introuvable")
    candidate.processing_status = new_status
    await db.commit()
    return {"status": new_status}


@router.get("/", response_model=list[CandidateResponse])
async def list_candidates(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Liste tous les candidats."""
    result = await db.execute(select(Candidate).order_by(Candidate.created_at.desc()))
    return result.scalars().all()


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Récupère un candidat par son ID."""
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidat introuvable")
    return candidate


@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    data: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Crée un candidat manuellement."""
    candidate = Candidate(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        location=data.location,
        availability=data.availability,
        created_by=uuid.UUID(user["sub"]),
    )
    db.add(candidate)
    await db.flush()
    await db.refresh(candidate)
    return candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Supprime un candidat et ses données associées."""
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidat introuvable")
    await db.delete(candidate)
