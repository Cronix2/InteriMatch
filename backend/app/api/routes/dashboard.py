"""
InteriMatch AI - Routes Dashboard (analytiques)
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Candidate, MatchingResult, GeneratedEmail, JobOffer
from app.schemas.schemas import DashboardStatsResponse

router = APIRouter()


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne les statistiques du dashboard."""

    total_candidates = (await db.execute(select(func.count(Candidate.id)))).scalar() or 0
    total_matchings = (await db.execute(select(func.count(MatchingResult.id)))).scalar() or 0
    total_emails = (await db.execute(select(func.count(GeneratedEmail.id)))).scalar() or 0
    emails_validated = (
        await db.execute(
            select(func.count(GeneratedEmail.id)).where(GeneratedEmail.status == "validated")
        )
    ).scalar() or 0
    avg_score = (
        await db.execute(select(func.avg(MatchingResult.global_score)))
    ).scalar() or 0.0

    # Derniers matchings
    recent_query = (
        select(MatchingResult, JobOffer, Candidate)
        .join(JobOffer, MatchingResult.job_offer_id == JobOffer.id)
        .join(Candidate, MatchingResult.candidate_id == Candidate.id)
        .order_by(MatchingResult.computed_at.desc())
        .limit(8)
    )
    recent_rows = (await db.execute(recent_query)).all()
    recent_matchings = []
    for matching, offer, candidate in recent_rows:
        name = f"{candidate.first_name or ''} {candidate.last_name or ''}".strip() or "Candidat"
        recent_matchings.append({
            "id": str(matching.id),
            "candidate_name": name,
            "job_title": offer.title,
            "company_name": offer.company_name or "",
            "score": round(matching.global_score, 1),
            "date": matching.computed_at.isoformat() if matching.computed_at else "",
        })

    return DashboardStatsResponse(
        total_candidates=total_candidates,
        total_matchings=total_matchings,
        total_emails=total_emails,
        emails_validated=emails_validated,
        average_score=round(avg_score, 1),
        recent_matchings=recent_matchings,
    )
