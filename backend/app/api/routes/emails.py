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
)
from app.schemas.schemas import (
    GeneratedEmailResponse,
    EmailGenerateRequest,
    EmailUpdateRequest,
)
from app.services.email_generator import generate_candidate_email
from app.api.deps import get_current_user_db
from app.api.routes.recruiter import _extract_contact_from_raw
from app.services.hunter import find_email_by_domain, extract_domain_from_url

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Domains that are job boards — useless to query Hunter.io with
_JOB_BOARD_DOMAINS = {
    "francetravail.fr", "pole-emploi.fr", "indeed.com", "linkedin.com",
    "hellowork.com", "apec.fr", "monster.fr", "meteojob.com",
    "cadreemploi.fr", "jobteaser.com", "welcometothejungle.com",
    "regionsjob.com", "cadremploi.fr", "jobijoba.com",
}


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
        if d and d not in _JOB_BOARD_DOMAINS:
            domain = d
    if not domain and recruiter_contact.get("application_url"):
        url = recruiter_contact["application_url"]
        if not url.startswith("mailto:"):
            d = extract_domain_from_url(url)
            if d and d not in _JOB_BOARD_DOMAINS:
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
