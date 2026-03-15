"""
InteriMatch AI - Service d'intégration API France Travail
Gère l'authentification OAuth2 et la recherche d'offres.
"""

import time
import logging

import httpx

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Cache simple du token en mémoire
_token_cache: dict = {"access_token": None, "expires_at": 0}


async def _get_access_token() -> str:
    """Obtient un token OAuth2 pour l'API France Travail (avec cache)."""
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.france_travail_auth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.france_travail_client_id,
                "client_secret": settings.france_travail_client_secret,
                "scope": "api_offresdemploiv2 o2dsoffre",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 1500)
    return data["access_token"]


async def search_offers(
    keywords: str,
    commune: str | None = None,
    departement: str | None = None,
    type_contrat: str | None = None,
    experience: str | None = None,
    distance: int | None = None,
    page: int = 0,
    max_results: int = 20,
) -> dict:
    """
    Recherche des offres d'emploi sur l'API France Travail.
    Retourne les résultats bruts de l'API.
    """
    token = await _get_access_token()

    params = {"motsCles": keywords, "range": f"{page * max_results}-{(page + 1) * max_results - 1}"}
    if commune:
        params["commune"] = commune
    if departement:
        params["departement"] = departement
    if type_contrat:
        params["typeContrat"] = type_contrat
    if experience:
        params["experience"] = experience
    if distance:
        params["distance"] = distance

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.france_travail_base_url}/offres/search",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        response.raise_for_status()

    return response.json()


async def get_offer_detail(offer_id: str) -> dict:
    """Récupère le détail d'une offre spécifique."""
    token = await _get_access_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.france_travail_base_url}/offres/{offer_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        response.raise_for_status()

    return response.json()


def normalize_offer(raw_offer: dict) -> dict:
    """Normalise une offre brute de l'API en format interne."""
    lieu = raw_offer.get("lieuTravail", {})
    entreprise = raw_offer.get("entreprise", {})
    competences = raw_offer.get("competences", [])

    return {
        "api_source_id": raw_offer.get("id", ""),
        "title": raw_offer.get("intitule", ""),
        "company_name": entreprise.get("nom", "") if isinstance(entreprise, dict) else str(entreprise),
        "location": lieu.get("libelle", ""),
        "postal_code": lieu.get("codePostal", ""),
        "description": raw_offer.get("description", ""),
        "required_skills": [c.get("libelle", "") for c in competences if isinstance(c, dict)],
        "contract_type": raw_offer.get("typeContrat", ""),
        "experience_level": raw_offer.get("experienceExige", ""),
        "publication_date": raw_offer.get("dateCreation"),
        "salary_info": raw_offer.get("salaire", {}).get("libelle", "") if isinstance(raw_offer.get("salaire"), dict) else "",
        "raw_data": raw_offer,
    }
