"""
InteriMatch AI - Routes Génération & Gestion d'emails
"""

import io
import re
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fpdf import FPDF

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    MatchingResult,
    GeneratedEmail,
    Candidate,
    Resume,
    ExtractedProfile,
    JobOffer,
    User,
    UserSettings,
    SentProposal,
    CompanyContact,
)
from app.schemas.schemas import (
    GeneratedEmailResponse,
    EmailGenerateRequest,
    EmailUpdateRequest,
)
from app.services.email_generator import generate_candidate_email
from app.api.deps import get_current_user_db
from app.api.routes.recruiter import _extract_contact_from_raw
from app.services.hunter import find_email_by_domain, extract_domain_from_url, fetch_company_contacts, clean_company_name

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Domains that are job boards — useless to query Hunter.io with
_JOB_BOARD_ROOTS = [
    "francetravail.fr", "pole-emploi.fr", "indeed.com", "linkedin.com",
    "hellowork.com", "apec.fr", "monster.fr", "meteojob.com",
    "cadreemploi.fr", "jobteaser.com", "welcometothejungle.com",
    "regionsjob.com", "cadremploi.fr", "jobijoba.com",
]


def _is_job_board_domain(domain: str) -> bool:
    """Check if a domain belongs to a job board (including subdomains like candidat.francetravail.fr)."""
    d = domain.lower().strip()
    return any(d == jb or d.endswith(f".{jb}") for jb in _JOB_BOARD_ROOTS)


def _is_valid_email(value: str | None) -> bool:
    return bool(value and _EMAIL_RE.match(value))


async def _hunter_lookup(user_settings, recruiter_contact: dict) -> str | None:
    """Try Hunter.io to find a recruiter email. Returns email string or None."""
    if not (user_settings and user_settings.hunter_api_key):
        return None
    domain = None
    # Prefer company_url (the company's own site) over application_url (job board)
    if recruiter_contact.get("company_url"):
        d = extract_domain_from_url(recruiter_contact["company_url"])
        if d and not _is_job_board_domain(d):
            domain = d
    if not domain and recruiter_contact.get("application_url"):
        url = recruiter_contact["application_url"]
        if not url.startswith("mailto:"):
            d = extract_domain_from_url(url)
            if d and not _is_job_board_domain(d):
                domain = d
    if not domain:
        return None
    contact_name = recruiter_contact.get("contact_name", "")
    parts = contact_name.split() if contact_name else []
    first_name = parts[0] if len(parts) >= 2 else None
    last_name = parts[-1] if len(parts) >= 2 else None
    result = await find_email_by_domain(user_settings.hunter_api_key, domain, first_name, last_name)
    if result and result.get("email"):
        return result["email"]
    return None


@router.post("/generate", response_model=GeneratedEmailResponse, status_code=201)
async def generate_email(
    request: EmailGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """
    Génère un email professionnel pour une correspondance candidat/offre.
    """
    # Récupérer le matching avec les relations
    result = await db.execute(
        select(MatchingResult)
        .options(selectinload(MatchingResult.job_offer))
        .where(MatchingResult.id == request.matching_result_id)
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Résultat de matching introuvable")

    # Idempotence: si un email existe déjà pour ce matching, le renvoyer directement
    existing_result = await db.execute(
        select(GeneratedEmail).where(GeneratedEmail.matching_result_id == match.id)
    )
    existing_email = existing_result.scalar_one_or_none()
    if existing_email:
        # If recruiter_email is missing or invalid, try to (re-)resolve it with Hunter.io
        if not _is_valid_email(existing_email.recruiter_email):
            recruiter_contact = _extract_contact_from_raw(
                match.job_offer.raw_data if hasattr(match.job_offer, "raw_data") else None
            )
            fresh_email = recruiter_contact.get("contact_email")
            if not _is_valid_email(fresh_email):
                fresh_email = await _hunter_lookup(user.settings, recruiter_contact)
            if _is_valid_email(fresh_email):
                existing_email.recruiter_email = fresh_email
                await db.flush()
                await db.refresh(existing_email)
        return existing_email

    # Récupérer le profil du candidat
    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.resumes).selectinload(Resume.extracted_profile))
        .where(Candidate.id == match.candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate or not candidate.resumes:
        raise HTTPException(status_code=400, detail="Candidat ou CV introuvable")

    latest_resume = sorted(candidate.resumes, key=lambda r: r.imported_at, reverse=True)[0]
    profile = latest_resume.extracted_profile
    if not profile:
        raise HTTPException(status_code=400, detail="Profil extrait introuvable")

    # Préparer les données
    profile_dict = {
        "skills": profile.skills or [],
        "experiences": profile.experiences or [],
        "education": profile.education or [],
        "profile_summary": profile.profile_summary,
        "years_of_experience": profile.years_of_experience,
    }
    candidate_dict = {
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "location": candidate.location,
        "availability": candidate.availability,
    }
    offer_dict = {
        "title": match.job_offer.title,
        "company_name": match.job_offer.company_name,
        "location": match.job_offer.location,
        "description": match.job_offer.description or "",
    }

    # Préparer les données agence
    agency_info = {}
    if user.settings:
        s = user.settings
        agency_info = {
            "agency_name": s.company_name or "",
            "agency_address": s.agency_address or "",
            "agency_phone": s.agency_phone or "",
            "agency_email": s.agency_email or "",
            "recruiter_name": f"{s.first_name or ''} {s.last_name or ''}".strip(),
        }

    # Générer le mail via IA
    try:
        email_data = await generate_candidate_email(
            profile=profile_dict,
            candidate=candidate_dict,
            offer=offer_dict,
            match_score=match.global_score,
            match_explanation=match.explanation or "",
            agency_info=agency_info,
            email_template=user.settings.email_template if user.settings else "",
            user_id=str(user.id),
            user_settings=user.settings,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur du service IA lors de la génération de l'email : {exc}",
        )

    # Extraire l'email du recruteur depuis les données brutes de l'offre
    recruiter_contact = _extract_contact_from_raw(
        match.job_offer.raw_data if hasattr(match.job_offer, "raw_data") else None
    )
    recruiter_email_addr = recruiter_contact.get("contact_email")
    # Validate: only keep if it's a real email address
    if not _is_valid_email(recruiter_email_addr):
        recruiter_email_addr = None

    # Fallback Hunter.io si pas d'email et clé configurée
    if not recruiter_email_addr:
        recruiter_email_addr = await _hunter_lookup(user.settings, recruiter_contact)

    # Sauvegarder
    generated_email = GeneratedEmail(
        matching_result_id=match.id,
        subject=email_data["subject"],
        body=email_data["body"],
        recruiter_email=recruiter_email_addr,
        status="draft",
    )
    db.add(generated_email)
    try:
        await db.flush()
        await db.refresh(generated_email)
    except IntegrityError:
        await db.rollback()
        # Requête concurrente/dupliquée : retourner la version déjà créée
        existing_after_race_result = await db.execute(
            select(GeneratedEmail).where(GeneratedEmail.matching_result_id == match.id)
        )
        existing_after_race = existing_after_race_result.scalar_one_or_none()
        if existing_after_race:
            return existing_after_race
        raise

    return generated_email


@router.get("/company-contacts-by-name")
async def get_company_contacts_by_name(
    company: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """
    Recherche les contacts d'une entreprise par nom via Hunter.io.
    Étape 1 : nettoie le nom brut (ex: "SYNERGIE - voir rce 26000799" → "SYNERGIE").
    Étape 2 : Hunter résout le domaine (ex: "SYNERGIE" → synergie.fr).
    Étape 3 : Hunter retourne les contacts du domaine trouvé.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Step 1 — Clean the company name from France Travail noise
    raw_company = company.strip()
    company = clean_company_name(raw_company)
    logger.info("Company name cleaned: '%s' -> '%s'", raw_company, company)
    if not company:
        return {"cleaned_name": raw_company, "domain": None, "contacts": []}

    # Check cache: look for any domain that matches this company name
    result = await db.execute(
        select(CompanyContact).where(
            CompanyContact.company_name.ilike(f"%{company}%"),
            CompanyContact.fetched_by == user.id,
        )
    )
    cached = result.scalars().all()
    if cached:
        logger.info("Found %d cached contacts for company '%s'", len(cached), company)
        # Infer domain from cache
        cached_domain = cached[0].domain if cached else None
        return {
            "cleaned_name": company,
            "domain": cached_domain,
            "contacts": [
                {
                    "id": str(c.id),
                    "email": c.email,
                    "first_name": c.first_name,
                    "last_name": c.last_name,
                    "position": c.position,
                    "department": c.department,
                    "confidence": c.confidence,
                    "company_name": c.company_name,
                }
                for c in cached
            ],
        }

    # No cache — call Hunter.io by company name
    # Step 2: Hunter resolves company name → domain
    # Step 3: Hunter returns contacts at that domain
    if not (user.settings and user.settings.hunter_api_key):
        logger.warning("No Hunter API key configured for user %s", user.id)
        return {"cleaned_name": company, "domain": None, "contacts": []}

    logger.info("Calling Hunter.io domain-search by company name: '%s'", company)
    result_data = await fetch_company_contacts(
        user.settings.hunter_api_key, company_name=company
    )
    contacts = result_data.get("contacts", [])
    organization = result_data.get("organization", "") or company
    resolved_domain = result_data.get("domain", "")
    logger.info(
        "Hunter returned %d contacts, org=%s, domain=%s for company '%s'",
        len(contacts), organization, resolved_domain, company,
    )

    if not contacts:
        return {"cleaned_name": company, "domain": resolved_domain or None, "contacts": []}

    # Save to cache (use the domain Hunter resolved)
    cache_domain = resolved_domain or company.lower().replace(" ", "")
    saved = []
    for c in contacts:
        cc = CompanyContact(
            domain=cache_domain,
            email=c["email"],
            first_name=c.get("first_name", ""),
            last_name=c.get("last_name", ""),
            position=c.get("position", ""),
            department=c.get("department", ""),
            confidence=c.get("confidence", 0),
            company_name=organization,
            fetched_by=user.id,
        )
        db.add(cc)
        saved.append({
            "email": c["email"],
            "first_name": c.get("first_name", ""),
            "last_name": c.get("last_name", ""),
            "position": c.get("position", ""),
            "department": c.get("department", ""),
            "confidence": c.get("confidence", 0),
            "company_name": organization,
        })
    await db.flush()

    return {"cleaned_name": company, "domain": resolved_domain or cache_domain, "contacts": saved}


@router.get("/company-contacts/{domain}")
async def get_company_contacts(
    domain: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """
    Récupère les contacts d'une entreprise (cache DB ou Hunter.io).
    Retourne une liste de contacts avec email, nom, position, département.
    """
    import logging
    logger = logging.getLogger(__name__)

    domain = domain.strip().lower()
    logger.info("Company contacts request for domain: %s", domain)

    # Check cache first
    result = await db.execute(
        select(CompanyContact).where(
            CompanyContact.domain == domain,
            CompanyContact.fetched_by == user.id,
        )
    )
    cached = result.scalars().all()
    if cached:
        logger.info("Found %d cached contacts for %s", len(cached), domain)
        return [
            {
                "id": str(c.id),
                "email": c.email,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "position": c.position,
                "department": c.department,
                "confidence": c.confidence,
                "company_name": c.company_name,
            }
            for c in cached
        ]

    # No cache — call Hunter.io
    if not (user.settings and user.settings.hunter_api_key):
        logger.warning("No Hunter API key configured for user %s", user.id)
        return []

    logger.info("Calling Hunter.io domain-search for %s", domain)
    result_data = await fetch_company_contacts(user.settings.hunter_api_key, domain)
    contacts = result_data.get("contacts", [])
    organization = result_data.get("organization", "")
    logger.info("Hunter returned %d contacts, org=%s for %s", len(contacts), organization, domain)

    if not contacts:
        return []

    # Save to cache
    saved = []
    for c in contacts:
        cc = CompanyContact(
            domain=domain,
            email=c["email"],
            first_name=c.get("first_name", ""),
            last_name=c.get("last_name", ""),
            position=c.get("position", ""),
            department=c.get("department", ""),
            confidence=c.get("confidence", 0),
            company_name=organization,
            fetched_by=user.id,
        )
        db.add(cc)
        saved.append({
            "email": c["email"],
            "first_name": c.get("first_name", ""),
            "last_name": c.get("last_name", ""),
            "position": c.get("position", ""),
            "department": c.get("department", ""),
            "confidence": c.get("confidence", 0),
            "company_name": organization,
        })
    await db.flush()

    return saved


@router.get("/{email_id}", response_model=GeneratedEmailResponse)
async def get_email(
    email_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Récupère un email généré."""
    result = await db.execute(select(GeneratedEmail).where(GeneratedEmail.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email introuvable")
    return email


@router.put("/{email_id}", response_model=GeneratedEmailResponse)
async def update_email(
    email_id: uuid.UUID,
    data: EmailUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Mettre à jour un email (édition manuelle, validation)."""
    result = await db.execute(select(GeneratedEmail).where(GeneratedEmail.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email introuvable")

    if data.subject is not None:
        email.subject = data.subject
    if data.body is not None:
        email.body = data.body
    if data.status is not None:
        email.status = data.status
        if data.status == "validated":
            email.validated_at = datetime.now(timezone.utc)
            # Créer un enregistrement SentProposal
            match_result = await db.execute(
                select(MatchingResult).where(MatchingResult.id == email.matching_result_id)
            )
            match = match_result.scalar_one_or_none()
            if match:
                proposal = SentProposal(
                    job_offer_id=match.job_offer_id,
                    candidate_id=match.candidate_id,
                    email_id=email.id,
                )
                db.add(proposal)

    await db.flush()
    await db.refresh(email)
    return email


def _generate_anonymized_pdf(profile) -> bytes:
    """Generate anonymized CV PDF bytes from an ExtractedProfile."""

    def safe(text: str | None) -> str:
        if not text:
            return ""
        return text.encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "CV Anonyme", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    if profile.professional_domain or profile.desired_job_titles:
        pdf.set_font("Helvetica", "I", 12)
        domain = safe(profile.professional_domain)
        titles = safe(", ".join(profile.desired_job_titles or []))
        header = domain if domain else titles
        pdf.cell(0, 8, header, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(2)

    if profile.mobility:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, safe(f"Zone de mobilit\u00e9 : {profile.mobility}"), new_x="LMARGIN", new_y="NEXT", align="C")

    if profile.years_of_experience:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, safe(f"{profile.years_of_experience} an(s) d'exp\u00e9rience"), new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(6)

    def section_title(title: str):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 9, safe(f"  {title}"), new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(3)

    if profile.profile_summary:
        section_title("Profil")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, safe(profile.profile_summary))
        pdf.ln(4)

    if profile.skills:
        section_title("Comp\u00e9tences")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, safe(", ".join(profile.skills)))
        pdf.ln(4)

    if profile.experiences:
        section_title("Exp\u00e9riences professionnelles")
        for exp in profile.experiences:
            pdf.set_font("Helvetica", "B", 10)
            title_text = safe(exp.get("title", ""))
            company = safe(exp.get("company", ""))
            duration = safe(exp.get("duration", ""))
            pdf.cell(0, 6, f"{title_text} - {company}", new_x="LMARGIN", new_y="NEXT")
            if duration:
                pdf.set_font("Helvetica", "I", 9)
                pdf.cell(0, 5, duration, new_x="LMARGIN", new_y="NEXT")
            desc = safe(exp.get("description", ""))
            if desc:
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, desc)
            pdf.ln(2)
        pdf.ln(2)

    if profile.education:
        section_title("Formation")
        for edu in profile.education:
            pdf.set_font("Helvetica", "B", 10)
            diploma = safe(edu.get("diploma", ""))
            school = safe(edu.get("school", ""))
            year = safe(str(edu.get("year", "")))
            pdf.cell(0, 6, f"{diploma} - {school}", new_x="LMARGIN", new_y="NEXT")
            if year:
                pdf.set_font("Helvetica", "I", 9)
                pdf.cell(0, 5, year, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        pdf.ln(2)

    if profile.certifications:
        section_title("Certifications")
        pdf.set_font("Helvetica", "", 10)
        for cert in profile.certifications:
            pdf.cell(0, 6, safe(f"- {cert}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    if profile.languages:
        section_title("Langues")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, safe(", ".join(profile.languages)), new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


@router.get("/{email_id}/download-eml")
async def download_email_eml(
    email_id: uuid.UUID,
    candidate_id: uuid.UUID = Query(..., description="ID du candidat pour joindre le CV anonymisé"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Génère un fichier .eml avec le CV anonymisé en pièce jointe."""
    # Load the email
    result = await db.execute(select(GeneratedEmail).where(GeneratedEmail.id == email_id))
    email_record = result.scalar_one_or_none()
    if not email_record:
        raise HTTPException(status_code=404, detail="Email introuvable")

    # Load candidate + profile for PDF generation
    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.resumes).selectinload(Resume.extracted_profile))
        .where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate or not candidate.resumes:
        raise HTTPException(status_code=404, detail="Candidat ou CV introuvable")

    latest_resume = sorted(candidate.resumes, key=lambda r: r.imported_at, reverse=True)[0]
    profile = latest_resume.extracted_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profil extrait introuvable")

    # Generate anonymized PDF
    pdf_bytes = _generate_anonymized_pdf(profile)

    # Build MIME email
    msg = MIMEMultipart()
    msg["Subject"] = email_record.subject or ""
    msg["To"] = email_record.recruiter_email or ""
    msg["From"] = ""

    msg.attach(MIMEText(email_record.body or "", "plain", "utf-8"))

    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename="cv_anonymise.pdf")
    msg.attach(attachment)

    buffer = io.BytesIO(msg.as_bytes())
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="message/rfc822",
        headers={"Content-Disposition": "attachment; filename=email_proposition.eml"},
    )


@router.put("/{email_id}/recipients")
async def update_email_recipients(
    email_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Met à jour le(s) destinataire(s) de l'email (chaîne, éventuellement plusieurs séparés par des virgules)."""
    result = await db.execute(select(GeneratedEmail).where(GeneratedEmail.id == email_id))
    email_record = result.scalar_one_or_none()
    if not email_record:
        raise HTTPException(status_code=404, detail="Email introuvable")

    recipients = body.get("recruiter_email", "")
    email_record.recruiter_email = recipients
    await db.flush()
    await db.refresh(email_record)
    return {"recruiter_email": email_record.recruiter_email}
