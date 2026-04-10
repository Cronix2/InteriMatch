"""
InteriMatch AI - Service de génération d'email
Génère un mail professionnel de proposition de candidat.
"""

import logging

from app.services.ai_service import generate_email as ai_generate_email

logger = logging.getLogger(__name__)


def _format_profile_for_email(profile: dict, candidate: dict) -> str:
    """Met en forme le profil candidat de façon ANONYME pour la génération de mail.
    Aucune information personnelle (nom, email, tel) n'est transmise au LLM."""
    lines = []
    if candidate.get("location"):
        lines.append(f"Zone géographique : {candidate['location']}")
    if candidate.get("availability"):
        lines.append(f"Disponibilité : {candidate['availability']}")
    if profile.get("profile_summary"):
        lines.append(f"Résumé du profil : {profile['profile_summary']}")
    if profile.get("skills"):
        lines.append(f"Compétences clés : {', '.join(profile['skills'][:10])}")
    if profile.get("years_of_experience"):
        lines.append(f"Années d'expérience : {profile['years_of_experience']}")
    if profile.get("experiences"):
        exp_lines = []
        for exp in profile["experiences"][:3]:
            exp_str = exp.get("title", "")
            if exp.get("duration"):
                exp_str += f" ({exp['duration']})"
            exp_lines.append(exp_str)
        if exp_lines:
            lines.append(f"Expériences récentes : {' | '.join(exp_lines)}")
    if profile.get("education"):
        edu_lines = []
        for edu in profile["education"][:2]:
            edu_lines.append(edu.get("diploma", ""))
        if edu_lines:
            lines.append(f"Formation : {', '.join(edu_lines)}")
    return "\n".join(lines)


async def generate_candidate_email(
    profile: dict,
    candidate: dict,
    offer: dict,
    match_score: float,
    match_explanation: str,
    agency_info: dict | None = None,
    email_template: str = "",
    user_id: str | None = None,
    user_settings=None,
) -> dict:
    """
    Génère un email professionnel pour proposer un candidat à une entreprise.
    
    Retourne : {"subject": str, "body": str}
    """
    candidate_text = _format_profile_for_email(profile, candidate)

    # Construire les infos agence pour le prompt
    agency_info = agency_info or {}
    agency_text = ""
    if any(agency_info.values()):
        parts = []
        if agency_info.get("recruiter_name"):
            parts.append(f"Signataire : {agency_info['recruiter_name']}")
        if agency_info.get("agency_name"):
            parts.append(f"Agence : {agency_info['agency_name']}")
        if agency_info.get("agency_phone"):
            parts.append(f"Tél : {agency_info['agency_phone']}")
        if agency_info.get("agency_email"):
            parts.append(f"Email : {agency_info['agency_email']}")
        if agency_info.get("agency_address"):
            parts.append(f"Adresse : {agency_info['agency_address']}")
        agency_text = "\n".join(parts)

    result = await ai_generate_email(
        candidate_profile=candidate_text,
        job_title=offer.get("title", ""),
        company_name=offer.get("company_name", ""),
        job_location=offer.get("location", ""),
        job_description=offer.get("description", "")[:800],
        match_score=match_score,
        match_explanation=match_explanation,
        agency_info=agency_text,
        email_template=email_template,
        user_id=user_id,
        user_settings=user_settings,
    )

    return {
        "subject": result.get("subject", "Proposition de candidature"),
        "body": result.get("body", ""),
    }
