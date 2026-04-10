"""
InteriMatch AI - Routes Matching candidat / offres
"""

import uuid
from typing import Any

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
    SentProposal,
    User,
)
from app.schemas.schemas import MatchingRequest, MatchingResultResponse
from app.services.france_travail import search_offers, normalize_offer
from app.services.matching import match_candidate_to_offers
from app.api.deps import get_current_user_db
from sqlalchemy import func

router = APIRouter()


def _safe_keyword(value: str | None) -> str:
    if not value:
        return ""
    normalized = " ".join(value.split()).strip()
    if len(normalized) <= 100:
        return normalized
    return normalized[:100].rsplit(" ", 1)[0]


def _build_keyword_candidates(request_keywords: str | None, profile: Any, candidate: Candidate) -> list[str]:
    """Construit une liste de recherches progressives: ciblée puis élargie."""
    candidates: list[str] = []

    def add(value: str | None):
        keyword = _safe_keyword(value)
        if keyword and keyword not in candidates:
            candidates.append(keyword)

    add(request_keywords)

    for title in (profile.desired_job_titles or [])[:3]:
        add(title)

    skills = profile.skills or []
    if skills:
        add(" ".join(skills[:3]))
        for skill in skills[:5]:
            add(skill)

    add(candidate.last_name)

    # Repli large pour garantir des offres même si le profil est très spécifique
    add("emploi")
    add("technicien")
    add("agent")

    return candidates


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


async def _fetch_offers_with_fallback(
    request: MatchingRequest,
    profile: Any,
    candidate: Candidate,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> list[dict]:
    """Récupère des offres avec élargissement progressif des critères."""
    target_count = max(3, min(request.max_results, 10))
    query_candidates = _build_keyword_candidates(request.keywords, profile, candidate)

    collected: dict[str, dict] = {}
    search_plans = [
        (request.location, request.department),
        (request.location, None),
        (None, request.department),
        (None, None),
    ]

    for keywords in query_candidates:
        for commune, departement in search_plans:
            if len(collected) >= target_count:
                break
            try:
                raw_results = await search_offers(
                    keywords=keywords,
                    commune=commune,
                    departement=departement,
                    type_contrat=request.contract_type,
                    max_results=target_count,
                    client_id=client_id,
                    client_secret=client_secret,
                )
            except Exception:
                continue

            for raw in raw_results.get("resultats", []):
                offer_id = raw.get("id")
                if offer_id and offer_id not in collected:
                    collected[offer_id] = raw

        if len(collected) >= target_count:
            break

    return list(collected.values())[:target_count]


@router.post("/compute", response_model=list[MatchingResultResponse])
async def compute_matching(
    request: MatchingRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """
    Lance le matching pour un candidat :
    1. Récupère le profil extrait
    2. Recherche les offres (France Travail ou en base)
    3. Calcule le score de matching via IA
    4. Sauvegarde les résultats
    """
    # Credentials utilisateur pour France Travail
    ft_cid = user.settings.france_travail_client_id if user.settings and user.settings.france_travail_client_id else None
    ft_cs = user.settings.france_travail_client_secret if user.settings and user.settings.france_travail_client_secret else None
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

    # Recherche progressive: d'abord ciblée, puis élargie pour garantir des propositions
    raw_offers = await _fetch_offers_with_fallback(request, profile, candidate, ft_cid, ft_cs)
    if not raw_offers:
        raise HTTPException(status_code=404, detail="Aucune offre trouvée (même après élargissement automatique des critères)")

    if len(raw_offers) < 3:
        existing_ids = {offer.get("id") for offer in raw_offers}
        fallback_count = 3 - len(raw_offers)
        fallback_result = await db.execute(
            select(JobOffer).order_by(JobOffer.fetched_at.desc()).limit(fallback_count * 3)
        )
        for fallback in fallback_result.scalars().all():
            if len(raw_offers) >= 3:
                break
            if fallback.api_source_id in existing_ids:
                continue
            raw_offers.append(fallback.raw_data or {
                "id": fallback.api_source_id,
                "intitule": fallback.title,
                "description": fallback.description,
                "entreprise": {"nom": fallback.company_name},
                "lieuTravail": {
                    "libelle": fallback.location,
                    "codePostal": fallback.postal_code,
                },
                "typeContrat": fallback.contract_type,
                "experienceExige": fallback.experience_level,
                "dateCreation": fallback.publication_date.isoformat() if fallback.publication_date else None,
                "competences": [{"libelle": s} for s in (fallback.required_skills or [])],
            })
            existing_ids.add(fallback.api_source_id)

    # Normaliser et sauvegarder les offres
    offers_data = []
    offer_models_by_source: dict[str, JobOffer] = {}
    for raw in raw_offers:
        normalized = normalize_offer(raw)
        offers_data.append(normalized)

        # Upsert en base
        existing_result = await db.execute(
            select(JobOffer).where(JobOffer.api_source_id == normalized["api_source_id"])
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            offer_models_by_source[normalized["api_source_id"]] = existing
        else:
            offer = JobOffer(**normalized)
            db.add(offer)
            await db.flush()
            await db.refresh(offer)
            offer_models_by_source[normalized["api_source_id"]] = offer

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
        user_id=str(user.id),
        user_settings=user.settings,
    )

    # Sauvegarder les résultats (avec mapping fiable offre <-> score)
    saved_results = []
    for match_data in matching_results:
        offer_id = (match_data.get("offer") or {}).get("api_source_id")
        offer_model = offer_models_by_source.get(offer_id)
        if not offer_model:
            continue

        match_result = MatchingResult(
            candidate_id=candidate.id,
            job_offer_id=offer_model.id,
            global_score=_safe_float(match_data.get("global_score")),
            skills_score=_safe_float(match_data.get("skills_score")),
            experience_score=_safe_float(match_data.get("experience_score")),
            location_score=_safe_float(match_data.get("location_score")),
            education_score=_safe_float(match_data.get("education_score")),
            job_title_score=_safe_float(match_data.get("job_title_score")),
            explanation=match_data.get("explanation"),
        )
        db.add(match_result)
        await db.flush()
        await db.refresh(match_result)
        match_result.job_offer = offer_model
        saved_results.append(match_result)

    # Trier par score décroissant
    saved_results.sort(key=lambda r: r.global_score, reverse=True)
    return saved_results[: max(3, min(request.max_results, 10))]


@router.get("/history", response_model=list[dict])
async def get_all_matchings_history(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Récupère l'historique complet des matchings avec infos candidat."""
    result = await db.execute(
        select(MatchingResult)
        .options(
            selectinload(MatchingResult.job_offer),
            selectinload(MatchingResult.candidate),
        )
        .order_by(MatchingResult.computed_at.desc())
        .limit(100)
    )
    matchings = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "global_score": m.global_score,
            "skills_score": m.skills_score,
            "experience_score": m.experience_score,
            "education_score": m.education_score,
            "job_title_score": m.job_title_score,
            "location_score": m.location_score,
            "explanation": m.explanation,
            "created_at": m.computed_at.isoformat() if m.computed_at else None,
            "candidate": {
                "id": str(m.candidate.id),
                "first_name": m.candidate.first_name,
                "last_name": m.candidate.last_name,
            } if m.candidate else None,
            "job_offer": {
                "id": str(m.job_offer.id),
                "title": m.job_offer.title,
                "company_name": m.job_offer.company_name,
                "location": m.job_offer.location,
                "contract_type": m.job_offer.contract_type,
            } if m.job_offer else None,
        }
        for m in matchings
    ]


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


@router.get("/proposals/counts")
async def get_proposal_counts(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Retourne le nombre de propositions envoyées par offre d'emploi."""
    result = await db.execute(
        select(
            SentProposal.job_offer_id,
            func.count(SentProposal.id).label("count"),
        )
        .group_by(SentProposal.job_offer_id)
    )
    rows = result.all()
    return {str(row.job_offer_id): row.count for row in rows}
