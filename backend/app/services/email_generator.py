"""
InteriMatch AI - Service de génération d'email
Génère un mail professionnel de proposition de candidat.
"""

import logging

from app.services.ai_service import generate_email as ai_generate_email

logger = logging.getLogger(__name__)


def _format_profile_for_email(profile: dict, candidate: dict) -> str:
    """Met en forme le profil candidat pour la génération de mail."""
    lines = []
    name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
    if name:
        lines.append(f"Nom : {name}")
    if candidate.get("email"):
        lines.append(f"Email : {candidate['email']}")
    if candidate.get("phone"):
        lines.append(f"Téléphone : {candidate['phone']}")
    if candidate.get("location"):
        lines.append(f"Localisation : {candidate['location']}")
    if candidate.get("availability"):
        lines.append(f"Disponibilité : {candidate['availability']}")
    if profile.get("profile_summary"):
        lines.append(f"Résumé : {profile['profile_summary']}")
    if profile.get("skills"):
        lines.append(f"Compétences clés : {', '.join(profile['skills'][:10])}")
    if profile.get("years_of_experience"):
        lines.append(f"Expérience : {profile['years_of_experience']} ans")
    if profile.get("experiences"):
        last_exp = profile["experiences"][0]
        exp_str = last_exp.get("title", "")
        if last_exp.get("company"):
            exp_str += f" chez {last_exp['company']}"
        lines.append(f"Dernier poste : {exp_str}")
    return "\n".join(lines)


async def generate_candidate_email(
    profile: dict,
    candidate: dict,
    offer: dict,
    match_score: float,
    match_explanation: str,
) -> dict:
    """
    Génère un email professionnel pour proposer un candidat à une entreprise.
    
    Retourne : {"subject": str, "body": str}
    """
    candidate_text = _format_profile_for_email(profile, candidate)

    result = await ai_generate_email(
        candidate_profile=candidate_text,
        job_title=offer.get("title", ""),
        company_name=offer.get("company_name", ""),
        job_location=offer.get("location", ""),
        job_description=offer.get("description", "")[:800],
        match_score=match_score,
        match_explanation=match_explanation,
    )

    return {
        "subject": result.get("subject", "Proposition de candidature"),
        "body": result.get("body", ""),
    }
