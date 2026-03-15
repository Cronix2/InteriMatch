"""
InteriMatch AI - Routes Matching candidat / offres
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    Candidate,
    Resume,
    ExtractedProfile,
    JobOffer,
    MatchingResult,
)
from app.schemas.schemas import MatchingRequest, MatchingResultResponse
from app.services.france_travail import search_offers, normalize_offer
from app.services.matching import match_candidate_to_offers

router = APIRouter()


@router.post("/compute", response_model=list[MatchingResultResponse])
async def compute_matching(
    request: MatchingRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Lance le matching pour un candidat :
    1. Récupère le profil extrait
    2. Recherche les offres (France Travail ou en base)
    3. Calcule le score de matching via IA
    4. Sauvegarde les résultats
    """
    # Récupérer le candidat et son profil
    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.resumes).selectinload(Resume.extracted_profile))
        .where(Candidate.id == request.candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidat introuvable")

    if not candidate.resumes:
        raise HTTPException(status_code=400, detail="Aucun CV uploadé pour ce candidat")

    # Prendre le dernier CV
    latest_resume = sorted(candidate.resumes, key=lambda r: r.imported_at, reverse=True)[0]
    profile = latest_resume.extracted_profile
    if not profile:
        raise HTTPException(status_code=400, detail="Aucun profil extrait pour ce CV")

    # Construire les mots-clés de recherche
    keywords = request.keywords
    if not keywords:
        # Utiliser les compétences et postes recherchés du profil
        terms = (profile.desired_job_titles or []) + (profile.skills or [])[:5]
        keywords = " ".join(terms) if terms else candidate.last_name or ""

    # Récupérer les offres depuis France Travail
    try:
        raw_results = await search_offers(
            keywords=keywords,
            commune=request.location,
            departement=request.department,
            type_contrat=request.contract_type,
            max_results=request.max_results,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur API France Travail : {str(e)}")

    raw_offers = raw_results.get("resultats", [])
    if not raw_offers:
        raise HTTPException(status_code=404, detail="Aucune offre trouvée pour ces critères")

    # Normaliser et sauvegarder les offres
    offers_data = []
    offer_models = []
    for raw in raw_offers:
        normalized = normalize_offer(raw)
        offers_data.append(normalized)

        # Upsert en base
        existing_result = await db.execute(
            select(JobOffer).where(JobOffer.api_source_id == normalized["api_source_id"])
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            offer_models.append(existing)
        else:
            offer = JobOffer(**normalized)
            db.add(offer)
            await db.flush()
            await db.refresh(offer)
            offer_models.append(offer)

    # Construire les données pour le matching
    profile_dict = {
        "skills": profile.skills or [],
        "experiences": profile.experiences or [],
        "education": profile.education or [],
        "certifications": profile.certifications or [],
        "languages": profile.languages or [],
        "mobility": profile.mobility,
        "profile_summary": profile.profile_summary,
        "years_of_experience": profile.years_of_experience,
        "desired_job_titles": profile.desired_job_titles or [],
    }
    candidate_dict = {
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "location": candidate.location,
        "availability": candidate.availability,
    }

    # Calcul du matching via IA
    matching_results = await match_candidate_to_offers(
        profile=profile_dict,
        candidate=candidate_dict,
        offers=offers_data,
    )

    # Sauvegarder les résultats
    saved_results = []
    for match_data, offer_model in zip(matching_results, offer_models):
        match_result = MatchingResult(
            candidate_id=candidate.id,
            job_offer_id=offer_model.id,
            global_score=match_data["global_score"],
            skills_score=match_data["skills_score"],
            experience_score=match_data["experience_score"],
            location_score=match_data["location_score"],
            education_score=match_data["education_score"],
            job_title_score=match_data["job_title_score"],
            explanation=match_data["explanation"],
        )
        db.add(match_result)
        await db.flush()
        await db.refresh(match_result)
        match_result.job_offer = offer_model
        saved_results.append(match_result)

    # Trier par score décroissant
    saved_results.sort(key=lambda r: r.global_score, reverse=True)
    return saved_results


@router.get("/candidate/{candidate_id}", response_model=list[MatchingResultResponse])
async def get_candidate_matchings(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Récupère les résultats de matching d'un candidat."""
    result = await db.execute(
        select(MatchingResult)
        .options(selectinload(MatchingResult.job_offer))
        .where(MatchingResult.candidate_id == candidate_id)
        .order_by(MatchingResult.global_score.desc())
    )
    return result.scalars().all()
