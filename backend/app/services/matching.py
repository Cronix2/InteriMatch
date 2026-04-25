"""
InteriMatch AI - Service de matching candidat / offre
Combine scoring par règles métier et scoring par IA.
"""

import asyncio
import json
import logging

from app.services.ai_service import compute_ai_matching

logger = logging.getLogger(__name__)

# Concurrence max d'appels LLM en parallèle pour le matching d'un candidat.
# Tient compte des rate-limits providers (Groq ~30 req/s, OpenAI ~3 req/s).
_MATCHING_CONCURRENCY = 5


def _format_profile_for_matching(profile: dict, candidate: dict) -> str:
    """Met en forme le profil candidat pour le prompt IA."""
    lines = []
    name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
    if name:
        lines.append(f"Nom : {name}")
    if candidate.get("location"):
        lines.append(f"Localisation : {candidate['location']}")
    if candidate.get("availability"):
        lines.append(f"Disponibilité : {candidate['availability']}")
    if profile.get("profile_summary"):
        lines.append(f"Résumé : {profile['profile_summary']}")
    if profile.get("skills"):
        lines.append(f"Compétences : {', '.join(profile['skills'])}")
    if profile.get("years_of_experience"):
        lines.append(f"Années d'expérience : {profile['years_of_experience']}")
    if profile.get("experiences"):
        exp_lines = []
        for exp in profile["experiences"]:
            exp_str = exp.get("title", "")
            if exp.get("company"):
                exp_str += f" chez {exp['company']}"
            if exp.get("duration"):
                exp_str += f" ({exp['duration']})"
            exp_lines.append(exp_str)
        lines.append(f"Expériences : {' | '.join(exp_lines)}")
    if profile.get("education"):
        edu_lines = []
        for edu in profile["education"]:
            edu_str = edu.get("diploma", "")
            if edu.get("school"):
                edu_str += f" - {edu['school']}"
            edu_lines.append(edu_str)
        lines.append(f"Formation : {' | '.join(edu_lines)}")
    if profile.get("languages"):
        lines.append(f"Langues : {', '.join(profile['languages'])}")
    if profile.get("desired_job_titles"):
        lines.append(f"Postes recherchés : {', '.join(profile['desired_job_titles'])}")

    return "\n".join(lines)


def _format_offer_for_matching(offer: dict) -> str:
    """Met en forme une offre d'emploi pour le prompt IA."""
    lines = [
        f"Intitulé : {offer.get('title', '')}",
        f"Entreprise : {offer.get('company_name', '')}",
        f"Lieu : {offer.get('location', '')}",
        f"Type contrat : {offer.get('contract_type', '')}",
    ]
    if offer.get("description"):
        # Limiter la description pour le prompt
        desc = offer["description"][:1000]
        lines.append(f"Description : {desc}")
    if offer.get("required_skills"):
        lines.append(f"Compétences requises : {', '.join(offer['required_skills'])}")
    if offer.get("experience_level"):
        lines.append(f"Expérience demandée : {offer['experience_level']}")
    return "\n".join(lines)


async def match_candidate_to_offers(
    profile: dict,
    candidate: dict,
    offers: list[dict],
    user_id: str | None = None,
    user_settings=None,
) -> list[dict]:
    """
    Calcule le matching entre un candidat et une liste d'offres.
    Utilise le LLM pour un scoring intelligent.
    
    Retourne une liste triée par score décroissant.
    """
    candidate_text = _format_profile_for_matching(profile, candidate)
    sem = asyncio.Semaphore(_MATCHING_CONCURRENCY)

    async def _score_one(offer: dict) -> dict:
        offer_text = _format_offer_for_matching(offer)
        async with sem:
            try:
                scores = await compute_ai_matching(
                    candidate_text,
                    offer_text,
                    user_id=user_id,
                    user_settings=user_settings,
                )
                return {
                    "offer": offer,
                    "global_score": scores.get("global_score", 0),
                    "skills_score": scores.get("skills_score", 0),
                    "experience_score": scores.get("experience_score", 0),
                    "location_score": scores.get("location_score", 0),
                    "education_score": scores.get("education_score", 0),
                    "job_title_score": scores.get("job_title_score", 0),
                    "explanation": scores.get("explanation", ""),
                }
            except Exception as e:
                logger.error(
                    "Erreur matching offre %s: %s",
                    offer.get("api_source_id"),
                    e,
                )
                return {
                    "offer": offer,
                    "global_score": 0,
                    "skills_score": 0,
                    "experience_score": 0,
                    "location_score": 0,
                    "education_score": 0,
                    "job_title_score": 0,
                    "explanation": f"Erreur lors du calcul: {str(e)}",
                }

    # Exécution parallèle (semaphore-bornée) — gros gain pour 5-10 offres
    results = await asyncio.gather(*(_score_one(o) for o in offers))

    # Tri par score global décroissant
    results.sort(key=lambda r: r["global_score"], reverse=True)
    return results
