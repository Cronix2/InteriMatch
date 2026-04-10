"""
InteriMatch AI - Service d'intégration API France Travail
Gère l'authentification OAuth2 et la recherche d'offres.
"""

import time
import logging
from datetime import datetime

import httpx

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Cache simple du token en mémoire — par clé (client_id)
_token_cache: dict[str, dict] = {}


async def _get_access_token(client_id: str | None = None, client_secret: str | None = None) -> str:
    """Obtient un token OAuth2 pour l'API France Travail (avec cache par client_id)."""
    cid = client_id or settings.france_travail_client_id
    csecret = client_secret or settings.france_travail_client_secret

    now = time.time()
    cached = _token_cache.get(cid, {})
    if cached.get("access_token") and cached.get("expires_at", 0) > now + 60:
        return cached["access_token"]

    auth_url = settings.france_travail_auth_url
    payload = {
        "grant_type": "client_credentials",
        "client_id": cid,
        "client_secret": csecret,
        "scope": "api_offresdemploiv2 o2dsoffre",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            auth_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code != 200:
            logger.error("Échec auth France Travail (%s): %s", response.status_code, response.text)
            response.raise_for_status()

        data = response.json()

    _token_cache[cid] = {
        "access_token": data["access_token"],
        "expires_at": now + data.get("expires_in", 1500),
    }
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
    client_id: str | None = None,
    client_secret: str | None = None,
) -> dict:
    """
    Recherche des offres d'emploi sur l'API France Travail.
    Retourne les résultats bruts de l'API.
    """
    token = await _get_access_token(client_id, client_secret)

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
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30.0,
        )
        # 204 No Content = aucun résultat
        if response.status_code == 204:
            return {"resultats": [], "contentRange": {"maxResult": 0}}

        # 206 Partial Content est normal (pagination par range)
        if response.status_code not in (200, 206):
            logger.error("Erreur recherche France Travail (%s): %s", response.status_code, response.text)
            response.raise_for_status()

    # Body vide => pas de résultats
    text = response.text.strip()
    if not text:
        return {"resultats": [], "contentRange": {"maxResult": 0}}

    try:
        return response.json()
    except ValueError:
        logger.error("Réponse France Travail non JSON (%s): %s", response.status_code, response.text[:500])
        return {"resultats": [], "contentRange": {"maxResult": 0}}


async def get_offer_detail(offer_id: str, client_id: str | None = None, client_secret: str | None = None) -> dict:
    """Récupère le détail d'une offre spécifique."""
    token = await _get_access_token(client_id, client_secret)

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

    publication_date = raw_offer.get("dateCreation")
    if isinstance(publication_date, str):
        try:
            publication_date = datetime.fromisoformat(publication_date.replace("Z", "+00:00"))
        except ValueError:
            publication_date = None

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
        "publication_date": publication_date,
        "salary_info": raw_offer.get("salaire", {}).get("libelle", "") if isinstance(raw_offer.get("salaire"), dict) else "",
        "raw_data": raw_offer,
    }
