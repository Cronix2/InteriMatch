"""
InteriMatch AI - Routes Offres d'emploi (France Travail)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import JobOffer, User
from app.schemas.schemas import JobOfferResponse, JobSearchRequest
from app.services.france_travail import search_offers, normalize_offer
from app.api.deps import get_current_user_db

router = APIRouter()


@router.post("/search", response_model=list[JobOfferResponse])
async def search_job_offers(
    request: JobSearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """
    Recherche des offres d'emploi via l'API France Travail.
    Les résultats sont sauvegardés en base pour le matching.
    """
    # Credentials utilisateur en priorité, sinon fallback global
    ft_cid = user.settings.france_travail_client_id if user.settings and user.settings.france_travail_client_id else None
    ft_cs = user.settings.france_travail_client_secret if user.settings and user.settings.france_travail_client_secret else None
    try:
        raw_results = await search_offers(
            keywords=request.keywords,
            commune=request.location,
            departement=request.department,
            type_contrat=request.contract_type,
            experience=request.experience,
            distance=request.distance,
            max_results=request.max_results,
            client_id=ft_cid,
            client_secret=ft_cs,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur API France Travail : {str(e)}")

    raw_offers = raw_results.get("resultats", [])
    saved_offers = []

    for raw in raw_offers:
        normalized = normalize_offer(raw)

        # Upsert : éviter les doublons
        result = await db.execute(
            select(JobOffer).where(JobOffer.api_source_id == normalized["api_source_id"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Mise à jour
            for key, value in normalized.items():
                if key != "raw_data":
                    setattr(existing, key, value)
            existing.raw_data = normalized["raw_data"]
            saved_offers.append(existing)
        else:
            offer = JobOffer(**normalized)
            db.add(offer)
            await db.flush()
            await db.refresh(offer)
            saved_offers.append(offer)

    return saved_offers


@router.get("/", response_model=list[JobOfferResponse])
async def list_saved_offers(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Liste les offres sauvegardées en base."""
    result = await db.execute(select(JobOffer).order_by(JobOffer.fetched_at.desc()).limit(100))
    return result.scalars().all()
