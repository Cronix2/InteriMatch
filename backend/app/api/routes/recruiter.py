"""
InteriMatch AI - Routes Recherche de recruteur
Extrait les informations de contact du recruteur depuis les données brutes France Travail.
"""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import JobOffer

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
    _user: dict = Depends(get_current_user),
):
    """Recherche les informations du recruteur pour une offre donnée."""
    result = await db.execute(
        select(JobOffer).where(JobOffer.id == job_offer_id)
    )
    offer = result.scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    contact_info = _extract_contact_from_raw(offer.raw_data)

    return {
        "job_offer_id": str(offer.id),
        "job_title": offer.title,
        "company_name": offer.company_name,
        "contact": contact_info,
        "has_contact": bool(contact_info.get("contact_name") or contact_info.get("contact_email")),
    }
