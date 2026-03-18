"""
InteriMatch AI - Routes Dashboard (analytiques)
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Candidate, MatchingResult, GeneratedEmail, JobOffer, ApiUsageLog
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


@router.get("/api-metrics")
async def get_api_metrics(
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne les métriques d'utilisation des APIs IA."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # Totaux globaux
    total_calls = (await db.execute(select(func.count(ApiUsageLog.id)))).scalar() or 0
    total_tokens_in = (await db.execute(select(func.coalesce(func.sum(ApiUsageLog.tokens_input), 0)))).scalar() or 0
    total_tokens_out = (await db.execute(select(func.coalesce(func.sum(ApiUsageLog.tokens_output), 0)))).scalar() or 0
    total_cost = (await db.execute(select(func.coalesce(func.sum(ApiUsageLog.estimated_cost), 0)))).scalar() or 0
    avg_latency = (await db.execute(select(func.avg(ApiUsageLog.latency_ms)))).scalar() or 0
    error_count = (await db.execute(
        select(func.count(ApiUsageLog.id)).where(ApiUsageLog.success == False)
    )).scalar() or 0

    # Par type d'action
    action_stats_query = (
        select(
            ApiUsageLog.action,
            func.count(ApiUsageLog.id).label("count"),
            func.coalesce(func.sum(ApiUsageLog.tokens_input), 0).label("tokens_in"),
            func.coalesce(func.sum(ApiUsageLog.tokens_output), 0).label("tokens_out"),
            func.coalesce(func.sum(ApiUsageLog.estimated_cost), 0).label("cost"),
            func.avg(ApiUsageLog.latency_ms).label("avg_latency"),
        )
        .group_by(ApiUsageLog.action)
    )
    action_rows = (await db.execute(action_stats_query)).all()
    by_action = [
        {
            "action": row.action,
            "count": row.count,
            "tokens_input": int(row.tokens_in),
            "tokens_output": int(row.tokens_out),
            "estimated_cost": round(float(row.cost), 4),
            "avg_latency_ms": round(float(row.avg_latency), 0),
        }
        for row in action_rows
    ]

    # Appels par jour (7 derniers jours)
    daily_query = (
        select(
            cast(ApiUsageLog.created_at, Date).label("day"),
            func.count(ApiUsageLog.id).label("count"),
            func.coalesce(func.sum(ApiUsageLog.estimated_cost), 0).label("cost"),
        )
        .where(ApiUsageLog.created_at >= seven_days_ago)
        .group_by(cast(ApiUsageLog.created_at, Date))
        .order_by(cast(ApiUsageLog.created_at, Date))
    )
    daily_rows = (await db.execute(daily_query)).all()
    daily = [
        {
            "date": row.day.isoformat() if row.day else "",
            "calls": row.count,
            "cost": round(float(row.cost), 4),
        }
        for row in daily_rows
    ]

    # 30 derniers jours
    monthly_calls = (await db.execute(
        select(func.count(ApiUsageLog.id)).where(ApiUsageLog.created_at >= thirty_days_ago)
    )).scalar() or 0
    monthly_cost = (await db.execute(
        select(func.coalesce(func.sum(ApiUsageLog.estimated_cost), 0)).where(ApiUsageLog.created_at >= thirty_days_ago)
    )).scalar() or 0

    return {
        "total_calls": total_calls,
        "total_tokens_input": int(total_tokens_in),
        "total_tokens_output": int(total_tokens_out),
        "total_estimated_cost": round(float(total_cost), 4),
        "average_latency_ms": round(float(avg_latency), 0),
        "error_count": error_count,
        "error_rate": round(error_count / max(total_calls, 1) * 100, 1),
        "by_action": by_action,
        "daily": daily,
        "monthly_calls": monthly_calls,
        "monthly_cost": round(float(monthly_cost), 4),
    }
