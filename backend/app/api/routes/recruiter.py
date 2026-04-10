"""
InteriMatch AI - Routes Recherche de recruteur
Extrait les informations de contact du recruteur depuis les données brutes France Travail.
Fallback sur l'API Hunter.io si aucun email n'est trouvé.
"""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import JobOffer, User
from app.api.deps import get_current_user_db
from app.services.hunter import find_email_by_domain, extract_domain_from_url

router = APIRouter()

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _extract_email_from_text(text: str) -> str | None:
    """Recherche une adresse email dans une chaîne de texte libre."""
    match = _EMAIL_RE.search(text)
    return match.group(0) if match else None


def _extract_contact_from_raw(raw_data: dict | None) -> dict:
    """Extrait les informations de contact depuis les données brutes de France Travail."""
    if not raw_data:
        return {}

    contact = raw_data.get("contact", {})
    entreprise = raw_data.get("entreprise", {})

    result = {}

    # Contact direct (champ "contact" de l'API France Travail)
    if isinstance(contact, dict):
        if contact.get("nom"):
            result["contact_name"] = contact["nom"]
        if contact.get("courriel"):
            result["contact_email"] = contact["courriel"]
        if contact.get("telephone"):
            result["contact_phone"] = contact["telephone"]

        # coordonnees1/2 contiennent parfois l'email en texte libre
        coord1 = contact.get("coordonnees1", "")
        coord2 = contact.get("coordonnees2", "")
        coord_parts = []
        if coord1:
            coord_parts.append(coord1)
        if coord2:
            coord_parts.append(coord2)
        if coord_parts:
            result["contact_info"] = " — ".join(coord_parts)

        # Si pas d'email trouvé dans courriel, chercher dans coordonnées
        if not result.get("contact_email"):
            for coord in (coord1, coord2):
                if coord:
                    found = _extract_email_from_text(coord)
                    if found:
                        result["contact_email"] = found
                        break

        if contact.get("urlPostulation"):
            result["application_url"] = contact["urlPostulation"]
            # urlPostulation peut être un mailto:
            url_post = contact["urlPostulation"]
            if not result.get("contact_email") and url_post.startswith("mailto:"):
                email_part = url_post[7:].split("?")[0]
                if _EMAIL_RE.fullmatch(email_part):
                    result["contact_email"] = email_part

    # Infos entreprise
    if isinstance(entreprise, dict):
        if entreprise.get("nom"):
            result["company_name"] = entreprise["nom"]
        if entreprise.get("url"):
            result["company_url"] = entreprise["url"]

    # Origine de l'offre
    if raw_data.get("origineOffre"):
        origine = raw_data["origineOffre"]
        if isinstance(origine, dict):
            if origine.get("urlOrigine"):
                result["source_url"] = origine["urlOrigine"]
                # urlOrigine peut aussi être un mailto:
                if not result.get("contact_email"):
                    url_orig = origine["urlOrigine"]
                    if url_orig.startswith("mailto:"):
                        email_part = url_orig[7:].split("?")[0]
                        if _EMAIL_RE.fullmatch(email_part):
                            result["contact_email"] = email_part
            if origine.get("origine"):
                result["source"] = origine["origine"]

    return result


@router.get("/job/{job_offer_id}")
async def lookup_recruiter(
    job_offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """Recherche les informations du recruteur pour une offre donnée.
    Utilise Hunter.io comme fallback si l'email n'est pas dans les données brutes."""
    result = await db.execute(
        select(JobOffer).where(JobOffer.id == job_offer_id)
    )
    offer = result.scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    contact_info = _extract_contact_from_raw(offer.raw_data)

    # Fallback Hunter.io si pas d'email trouvé dans les données brutes
    if not contact_info.get("contact_email") and user.settings and user.settings.hunter_api_key:
        hunter_key = user.settings.hunter_api_key
        # Chercher un domaine à partir de l'URL entreprise ou de l'URL de candidature
        domain = None
        if contact_info.get("company_url"):
            domain = extract_domain_from_url(contact_info["company_url"])
        elif contact_info.get("application_url") and not contact_info["application_url"].startswith("mailto:"):
            domain = extract_domain_from_url(contact_info["application_url"])
        elif contact_info.get("source_url") and not contact_info["source_url"].startswith("mailto:"):
            domain = extract_domain_from_url(contact_info["source_url"])

        if domain:
            # Extraire nom/prénom du contact si disponible
            contact_name = contact_info.get("contact_name", "")
            parts = contact_name.split() if contact_name else []
            first_name = parts[0] if len(parts) >= 2 else None
            last_name = parts[-1] if len(parts) >= 2 else None

            hunter_result = await find_email_by_domain(hunter_key, domain, first_name, last_name)
            if hunter_result and hunter_result.get("email"):
                contact_info["contact_email"] = hunter_result["email"]
                contact_info["email_source"] = hunter_result.get("source", "hunter")
                contact_info["email_confidence"] = hunter_result.get("confidence", 0)

    return {
        "job_offer_id": str(offer.id),
        "job_title": offer.title,
        "company_name": offer.company_name,
        "contact": contact_info,
        "has_contact": bool(contact_info.get("contact_name") or contact_info.get("contact_email")),
    }
