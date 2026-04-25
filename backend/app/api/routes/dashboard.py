"""
InteriMatch AI - Routes Dashboard (analytiques) — scopées à l'utilisateur courant.
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import (
    Candidate,
    MatchingResult,
    GeneratedEmail,
    JobOffer,
    ApiUsageLog,
    User,
)
from app.schemas.schemas import DashboardStatsResponse
from app.api.deps import get_current_user_db

router = APIRouter()


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Retourne les statistiques du dashboard pour l'utilisateur courant."""

    # Tous les compteurs sont scopés via Candidate.created_by
    total_candidates = (
        await db.execute(
            select(func.count(Candidate.id)).where(Candidate.created_by == user.id)
        )
    ).scalar() or 0

    total_matchings = (
        await db.execute(
            select(func.count(MatchingResult.id))
            .join(Candidate, MatchingResult.candidate_id == Candidate.id)
            .where(Candidate.created_by == user.id)
        )
    ).scalar() or 0

    total_emails = (
        await db.execute(
            select(func.count(GeneratedEmail.id))
            .join(MatchingResult, GeneratedEmail.matching_result_id == MatchingResult.id)
            .join(Candidate, MatchingResult.candidate_id == Candidate.id)
            .where(Candidate.created_by == user.id)
        )
    ).scalar() or 0

    emails_validated = (
        await db.execute(
            select(func.count(GeneratedEmail.id))
            .join(MatchingResult, GeneratedEmail.matching_result_id == MatchingResult.id)
            .join(Candidate, MatchingResult.candidate_id == Candidate.id)
            .where(Candidate.created_by == user.id, GeneratedEmail.status == "validated")
        )
    ).scalar() or 0

    avg_score = (
        await db.execute(
            select(func.avg(MatchingResult.global_score))
            .join(Candidate, MatchingResult.candidate_id == Candidate.id)
            .where(Candidate.created_by == user.id)
        )
    ).scalar() or 0.0

    # Derniers matchings (du user)
    recent_query = (
        select(MatchingResult, JobOffer, Candidate)
        .join(JobOffer, MatchingResult.job_offer_id == JobOffer.id)
        .join(Candidate, MatchingResult.candidate_id == Candidate.id)
        .where(Candidate.created_by == user.id)
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
    user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Retourne les métriques d'utilisation des APIs IA pour l'utilisateur courant."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    user_filter = ApiUsageLog.user_id == user.id

    # Totaux scopés au user
    total_calls = (
        await db.execute(select(func.count(ApiUsageLog.id)).where(user_filter))
    ).scalar() or 0
    total_tokens_in = (
        await db.execute(select(func.coalesce(func.sum(ApiUsageLog.tokens_input), 0)).where(user_filter))
    ).scalar() or 0
    total_tokens_out = (
        await db.execute(select(func.coalesce(func.sum(ApiUsageLog.tokens_output), 0)).where(user_filter))
    ).scalar() or 0
    total_cost = (
        await db.execute(select(func.coalesce(func.sum(ApiUsageLog.estimated_cost), 0)).where(user_filter))
    ).scalar() or 0
    avg_latency = (
        await db.execute(select(func.avg(ApiUsageLog.latency_ms)).where(user_filter))
    ).scalar() or 0
    error_count = (
        await db.execute(
            select(func.count(ApiUsageLog.id)).where(user_filter, ApiUsageLog.success == False)  # noqa: E712
        )
    ).scalar() or 0

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
        .where(user_filter)
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
            "avg_latency_ms": round(float(row.avg_latency or 0), 0),
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
        .where(user_filter, ApiUsageLog.created_at >= seven_days_ago)
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
    monthly_calls = (
        await db.execute(
            select(func.count(ApiUsageLog.id)).where(user_filter, ApiUsageLog.created_at >= thirty_days_ago)
        )
    ).scalar() or 0
    monthly_cost = (
        await db.execute(
            select(func.coalesce(func.sum(ApiUsageLog.estimated_cost), 0))
            .where(user_filter, ApiUsageLog.created_at >= thirty_days_ago)
        )
    ).scalar() or 0

    return {
        "total_calls": total_calls,
        "total_tokens_input": int(total_tokens_in),
        "total_tokens_output": int(total_tokens_out),
        "total_estimated_cost": round(float(total_cost), 4),
        "average_latency_ms": round(float(avg_latency or 0), 0),
        "error_count": error_count,
        "error_rate": round(error_count / max(total_calls, 1) * 100, 1),
        "by_action": by_action,
        "daily": daily,
        "monthly_calls": monthly_calls,
        "monthly_cost": round(float(monthly_cost), 4),
    }
