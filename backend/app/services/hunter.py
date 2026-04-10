"""
InteriMatch AI - Service Hunter.io
Recherche d'emails professionnels via l'API Hunter.io
"""

import logging
import re

import httpx

logger = logging.getLogger(__name__)

HUNTER_API_BASE = "https://api.hunter.io/v2"
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


async def find_email_by_domain(
    api_key: str,
    domain: str,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict | None:
    """
    Recherche un email via Hunter.io.
    Si first_name/last_name fournis → email-finder (email précis).
    Sinon → domain-search (emails du domaine).

    Retourne {"email": str, "confidence": int} ou None.
    """
    if not api_key or not domain:
        return None

    # Nettoyer le domaine (enlever http://, www., etc.)
    domain = domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    domain = domain.split("/")[0]

    if not domain or "." not in domain:
        return None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if first_name and last_name:
                # Email Finder — recherche précise
                resp = await client.get(
                    f"{HUNTER_API_BASE}/email-finder",
                    params={
                        "domain": domain,
                        "first_name": first_name,
                        "last_name": last_name,
                        "api_key": api_key,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    if data.get("email"):
                        return {
                            "email": data["email"],
                            "confidence": data.get("confidence", 0),
                            "source": "hunter_finder",
                        }

            # Domain Search — emails du domaine
            resp = await client.get(
                f"{HUNTER_API_BASE}/domain-search",
                params={
                    "domain": domain,
                    "api_key": api_key,
                    "limit": 5,
                },
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                emails = data.get("emails", [])
                if emails:
                    # Prendre l'email avec le meilleur confidence score
                    best = max(emails, key=lambda e: e.get("confidence", 0))
                    return {
                        "email": best["value"],
                        "confidence": best.get("confidence", 0),
                        "first_name": best.get("first_name", ""),
                        "last_name": best.get("last_name", ""),
                        "source": "hunter_domain",
                    }

    except Exception as e:
        logger.warning("Hunter.io API error: %s", e)

    return None


def extract_domain_from_url(url: str | None) -> str | None:
    """Extrait le domaine d'une URL."""
    if not url:
        return None
    url = url.strip().lower()
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    domain = url.split("/")[0]
    if "." in domain:
        return domain
    return None
