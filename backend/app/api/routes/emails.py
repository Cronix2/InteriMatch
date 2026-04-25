"""
InteriMatch AI - Routes Génération & Gestion d'emails
"""

import asyncio
import io
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
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

from app.core.database import get_db, async_session
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
    CompanyLookup,
)
from app.schemas.schemas import (
    GeneratedEmailResponse,
    EmailGenerateRequest,
    EmailUpdateRequest,
)
from app.services.email_generator import generate_candidate_email
from app.api.deps import get_current_user_db, get_owned_email, get_owned_matching, get_owned_candidate
from app.api.routes.recruiter import _extract_contact_from_raw
from app.services.hunter import find_email_by_domain, extract_domain_from_url, fetch_company_contacts, fetch_company_contacts_robust, fetch_company_contacts_full, clean_company_name
from app.services.smtp_service import (
    SmtpNotConfiguredError,
    SmtpSendError,
    resolve_smtp_config,
    send_email_smtp,
)

router = APIRouter()

logger = logging.getLogger(__name__)

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


# Durée de validité du cache des recherches Hunter
_HUNTER_CACHE_TTL_DAYS = 30


def _normalize_company_key(company_name: str) -> str:
    """Normalise un nom d'entreprise pour servir de clé de cache stable."""
    if not company_name:
        return ""
    s = re.sub(r"[^a-z0-9]+", "", company_name.lower())
    return s[:200]


def _build_lookup_key(domain: str | None, company_name: str | None) -> str | None:
    if domain:
        return f"domain:{domain.strip().lower()}"
    if company_name:
        slug = _normalize_company_key(company_name)
        if slug:
            return f"name:{slug}"
    return None


async def _get_cached_contacts(
    db: AsyncSession,
    user: User,
    *,
    domain: str | None,
    company_name: str | None,
) -> tuple[list[dict], str | None, str | None] | None:
    """Retourne (contacts, resolved_domain, resolved_company) si un cache frais
    existe, sinon None. Une liste vide signifie cache négatif (pas de contact).
    """
    key = _build_lookup_key(domain, company_name)
    if not key:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=_HUNTER_CACHE_TTL_DAYS)
    result = await db.execute(
        select(CompanyLookup)
        .where(
            CompanyLookup.user_id == user.id,
            CompanyLookup.lookup_key == key,
            CompanyLookup.fetched_at >= cutoff,
        )
        .order_by(CompanyLookup.fetched_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return None

    if row.contacts_count == 0:
        # Cache négatif
        return [], row.resolved_domain or None, row.resolved_company or None

    # Cache positif → on relit les contacts via le domaine résolu
    cache_domain = (row.resolved_domain or domain or "").strip().lower()
    if not cache_domain:
        return None
    res = await db.execute(
        select(CompanyContact).where(
            CompanyContact.domain == cache_domain,
            CompanyContact.fetched_by == user.id,
        )
    )
    cached = res.scalars().all()
    contacts = [
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
    return contacts, row.resolved_domain or None, row.resolved_company or None


async def _save_lookup_result(
    db: AsyncSession,
    user: User,
    *,
    domain: str | None,
    company_name: str | None,
    contacts: list[dict],
    resolved_domain: str | None,
    resolved_company: str | None,
) -> None:
    """Persiste le résultat d'une recherche Hunter (positif ou négatif)."""
    keys: list[str] = []
    k_domain = _build_lookup_key(domain, None)
    k_name = _build_lookup_key(None, company_name)
    if k_domain:
        keys.append(k_domain)
    if k_name and k_name not in keys:
        keys.append(k_name)
    if resolved_domain:
        k_resolved = _build_lookup_key(resolved_domain, None)
        if k_resolved and k_resolved not in keys:
            keys.append(k_resolved)
    if not keys:
        return
    for k in keys:
        db.add(
            CompanyLookup(
                user_id=user.id,
                lookup_key=k,
                resolved_domain=(resolved_domain or "")[:255],
                resolved_company=(resolved_company or "")[:255],
                contacts_count=len(contacts),
            )
        )


async def _get_or_fetch_company_contacts(
    db: AsyncSession,
    user: User,
    *,
    domain: str | None = None,
    company_name: str | None = None,
) -> dict:
    """Renvoie les contacts d'une entreprise depuis le cache, ou interroge Hunter
    et persiste le résultat (cache positif et négatif).

    Retourne un dict : {contacts, domain, organization, from_cache}.
    """
    if not (user.settings and user.settings.hunter_api_key):
        return {"contacts": [], "domain": domain, "organization": company_name or "", "from_cache": False}

    cached = await _get_cached_contacts(db, user, domain=domain, company_name=company_name)
    if cached is not None:
        contacts, cache_domain, cache_company = cached
        return {
            "contacts": contacts,
            "domain": cache_domain or domain,
            "organization": cache_company or company_name or "",
            "from_cache": True,
        }

    # Pas de cache frais → appel Hunter
    api_key = user.settings.hunter_api_key
    result_data = await fetch_company_contacts_full(
        api_key, domain=domain, company_name=company_name
    )
    contacts = result_data.get("contacts", []) or []
    organization = result_data.get("organization", "") or (company_name or "")
    resolved_domain = (result_data.get("domain") or domain or "").strip().lower()

    # Persister les contacts (clé = domaine résolu)
    saved: list[dict] = []
    if contacts and resolved_domain:
        for c in contacts:
            cc = CompanyContact(
                domain=resolved_domain,
                email=c["email"],
                first_name=c.get("first_name", "") or "",
                last_name=c.get("last_name", "") or "",
                position=c.get("position", "") or "",
                department=c.get("department", "") or "",
                confidence=c.get("confidence", 0) or 0,
                company_name=organization,
                fetched_by=user.id,
            )
            db.add(cc)
            saved.append({
                "email": c["email"],
                "first_name": c.get("first_name", "") or "",
                "last_name": c.get("last_name", "") or "",
                "position": c.get("position", "") or "",
                "department": c.get("department", "") or "",
                "confidence": c.get("confidence", 0) or 0,
                "company_name": organization,
            })

    await _save_lookup_result(
        db, user,
        domain=domain, company_name=company_name,
        contacts=saved, resolved_domain=resolved_domain or None,
        resolved_company=organization or None,
    )
    # Flush dans un savepoint pour ne PAS rollback la transaction parente
    # (ce qui expirerait tous les objets ORM partagés par la requête).
    try:
        async with db.begin_nested():
            await db.flush()
    except Exception as exc:
        logger.warning("Échec persistance cache Hunter : %s", exc)

    return {
        "contacts": saved,
        "domain": resolved_domain or domain,
        "organization": organization,
        "from_cache": False,
    }


async def _hunter_lookup(user_settings, recruiter_contact: dict, db: AsyncSession | None = None, user: User | None = None) -> str | None:
    """Try Hunter.io to find a recruiter email. Returns email string or None.
    Stratégie :
    1. Si on a un nom de contact + un domaine → email-finder précis
    2. Sinon → cache + fetch_company_contacts_full (Discover + patterns vérifiés)
    """
    if not (user_settings and user_settings.hunter_api_key):
        return None
    api_key = user_settings.hunter_api_key

    # Domaine
    domain = None
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

    contact_name = recruiter_contact.get("contact_name", "")
    parts = contact_name.split() if contact_name else []
    first_name = parts[0] if len(parts) >= 2 else None
    last_name = parts[-1] if len(parts) >= 2 else None

    # 1) Email finder précis si possible
    if domain and first_name and last_name:
        result = await find_email_by_domain(api_key, domain, first_name, last_name)
        if result and result.get("email"):
            return result["email"]

    # 2) Stratégie complète (cache → Discover + patterns)
    company_name = recruiter_contact.get("company_name") or ""
    cleaned = clean_company_name(company_name) if company_name else ""
    full: dict
    if db is not None and user is not None:
        full = await _get_or_fetch_company_contacts(
            db, user,
            domain=domain, company_name=cleaned or company_name or None,
        )
    else:
        # Fallback sans DB (pas de cache) — on appelle directement Hunter
        full = await fetch_company_contacts_full(
            api_key, domain=domain, company_name=cleaned or company_name or None,
        )
    contacts = full.get("contacts") or []
    if not contacts:
        return None

    # Préférer le 1er contact RH/recrutement (déjà trié par fetch_company_contacts)
    return contacts[0].get("email") or None


async def _generate_or_get_email_for_match(
    db: AsyncSession,
    user: User,
    match: MatchingResult,
) -> GeneratedEmail:
    """
    Renvoie l'email existant pour ce matching, ou en génère un nouveau et le persiste.
    Idempotent (peut être appelé en parallèle, gère IntegrityError).
    `match` doit avoir `.job_offer` eager-loaded.
    """
    # Idempotence
    existing_result = await db.execute(
        select(GeneratedEmail).where(GeneratedEmail.matching_result_id == match.id)
    )
    existing_email = existing_result.scalar_one_or_none()
    if existing_email:
        if not _is_valid_email(existing_email.recruiter_email):
            recruiter_contact = _extract_contact_from_raw(
                match.job_offer.raw_data if hasattr(match.job_offer, "raw_data") else None
            )
            fresh_email = recruiter_contact.get("contact_email")
            if not _is_valid_email(fresh_email):
                fresh_email = await _hunter_lookup(user.settings, recruiter_contact, db=db, user=user)
            if _is_valid_email(fresh_email):
                existing_email.recruiter_email = fresh_email
                await db.flush()
                await db.refresh(existing_email)
        return existing_email

    # Charger candidat + profil
    cand_result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.resumes).selectinload(Resume.extracted_profile))
        .where(Candidate.id == match.candidate_id)
    )
    candidate = cand_result.scalar_one_or_none()
    if not candidate or not candidate.resumes:
        raise HTTPException(status_code=400, detail="Candidat ou CV introuvable")

    latest_resume = sorted(candidate.resumes, key=lambda r: r.imported_at, reverse=True)[0]
    profile = latest_resume.extracted_profile
    if not profile:
        raise HTTPException(status_code=400, detail="Profil extrait introuvable")

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

    # Email recruteur (raw + fallback Hunter)
    recruiter_contact = _extract_contact_from_raw(
        match.job_offer.raw_data if hasattr(match.job_offer, "raw_data") else None
    )
    recruiter_email_addr = recruiter_contact.get("contact_email")
    if not _is_valid_email(recruiter_email_addr):
        recruiter_email_addr = None
    if not recruiter_email_addr:
        recruiter_email_addr = await _hunter_lookup(user.settings, recruiter_contact, db=db, user=user)

    generated_email = GeneratedEmail(
        matching_result_id=match.id,
        subject=email_data["subject"],
        body=email_data["body"],
        recruiter_email=recruiter_email_addr,
        status="draft",
    )
    db.add(generated_email)
    # Capturer l'id AVANT toute possible rollback : un rollback expire tous les
    # objets de la session et accéder à match.id ensuite déclenche un lazy-load
    # illégal en contexte async (MissingGreenlet).
    match_id = match.id
    try:
        await db.flush()
        await db.refresh(generated_email)
    except IntegrityError:
        await db.rollback()
        race_result = await db.execute(
            select(GeneratedEmail).where(GeneratedEmail.matching_result_id == match_id)
        )
        race_existing = race_result.scalar_one_or_none()
        if race_existing:
            return race_existing
        raise

    return generated_email


async def _precompute_one_email(matching_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """
    Pré-calcule un email pour un matching donné, dans une session DB indépendante.
    Toute exception est capturée et loggée — ne doit pas remonter (tâche fire-and-forget).
    """
    try:
        async with async_session() as session:
            # Recharger user (avec settings) + matching (avec offer) dans cette session
            user_result = await session.execute(
                select(User)
                .options(selectinload(User.settings))
                .where(User.id == user_id)
            )
            user_obj = user_result.scalar_one_or_none()
            if not user_obj:
                return
            match_result = await session.execute(
                select(MatchingResult)
                .join(Candidate, MatchingResult.candidate_id == Candidate.id)
                .where(MatchingResult.id == matching_id, Candidate.created_by == user_id)
                .options(selectinload(MatchingResult.job_offer))
            )
            match_obj = match_result.scalar_one_or_none()
            if not match_obj:
                return
            await _generate_or_get_email_for_match(session, user_obj, match_obj)
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pré-calcul email échoué pour matching=%s : %s", matching_id, exc)


async def precompute_top_emails(
    user_id: uuid.UUID,
    matching_ids: list[uuid.UUID],
    *,
    concurrency: int = 3,
) -> None:
    """
    Pré-calcule en parallèle (borné) les emails pour les meilleurs matchings.
    Appelée en tâche de fond après `compute_matching`.
    """
    if not matching_ids:
        return
    sem = asyncio.Semaphore(concurrency)

    async def _bound(mid: uuid.UUID) -> None:
        async with sem:
            await _precompute_one_email(mid, user_id)

    await asyncio.gather(*[_bound(mid) for mid in matching_ids], return_exceptions=True)


@router.post("/generate", response_model=GeneratedEmailResponse, status_code=201)
async def generate_email(
    request: EmailGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """
    Génère un email professionnel pour une correspondance candidat/offre.
    Idempotent : renvoie l'email déjà généré (ex. par le pré-calcul) si présent.
    """
    match = await get_owned_matching(
        request.matching_result_id, db, user, with_offer=True
    )
    return await _generate_or_get_email_for_match(db, user, match)


@router.get("/by-matching/{matching_id}", response_model=GeneratedEmailResponse)
async def get_email_by_matching(
    matching_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """Renvoie l'email pré-calculé pour ce matching (404 si pas encore prêt)."""
    match = await get_owned_matching(matching_id, db, user)
    res = await db.execute(
        select(GeneratedEmail).where(GeneratedEmail.matching_result_id == match.id)
    )
    email = res.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email pas encore généré")
    return email


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

    full = await _get_or_fetch_company_contacts(db, user, company_name=company)
    logger.info(
        "company-contacts-by-name '%s' → %d contacts (cache=%s, domain=%s)",
        company, len(full["contacts"]), full["from_cache"], full["domain"],
    )
    return {
        "cleaned_name": company,
        "domain": full["domain"],
        "contacts": full["contacts"],
    }


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

    full = await _get_or_fetch_company_contacts(db, user, domain=domain)
    logger.info(
        "company-contacts/%s → %d contacts (cache=%s)",
        domain, len(full["contacts"]), full["from_cache"],
    )
    return full["contacts"]


@router.get("/{email_id}", response_model=GeneratedEmailResponse)
async def get_email(
    email_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """Récupère un email généré (uniquement si propriétaire du matching)."""
    return await get_owned_email(email_id, db, user)


@router.put("/{email_id}", response_model=GeneratedEmailResponse)
async def update_email(
    email_id: uuid.UUID,
    data: EmailUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """Mettre à jour un email (édition, validation) — uniquement si propriétaire."""
    email = await get_owned_email(email_id, db, user)

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
    user: User = Depends(get_current_user_db),
):
    """Génère un fichier .eml avec le CV anonymisé (uniquement si propriétaire)."""
    email_record = await get_owned_email(email_id, db, user)
    candidate = await get_owned_candidate(candidate_id, db, user, with_resumes=True)
    if not candidate.resumes:
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
    user: User = Depends(get_current_user_db),
):
    """Met à jour le(s) destinataire(s) de l'email (uniquement si propriétaire)."""
    email_record = await get_owned_email(email_id, db, user)

    recipients = body.get("recruiter_email", "")
    email_record.recruiter_email = recipients
    await db.flush()
    await db.refresh(email_record)
    return {"recruiter_email": email_record.recruiter_email}


@router.get("/smtp/status")
async def get_smtp_status(user: User = Depends(get_current_user_db)):
    """Indique si l'envoi SMTP est utilisable (pour afficher/cacher le bouton frontend)."""
    cfg = resolve_smtp_config(user.settings)
    return {
        "configured": cfg.is_complete,
        "host": cfg.host,
        "port": cfg.port,
        "from": cfg.sender,
    }


@router.post("/{email_id}/send")
async def send_email(
    email_id: uuid.UUID,
    candidate_id: uuid.UUID = Query(..., description="ID du candidat (CV anonymisé en pièce jointe)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_db),
):
    """
    Envoie l'email via SMTP au(x) destinataire(s) défini(s) dans `recruiter_email`,
    avec le CV anonymisé du candidat en pièce jointe (PDF). Crée une SentProposal
    et marque GeneratedEmail.status = 'sent'.
    """
    email_record = await get_owned_email(email_id, db, user)
    candidate = await get_owned_candidate(candidate_id, db, user, with_resumes=True)

    if not email_record.recruiter_email or not email_record.recruiter_email.strip():
        raise HTTPException(status_code=400, detail="Aucun destinataire defini pour cet email.")

    if not candidate.resumes:
        raise HTTPException(status_code=400, detail="Aucun CV disponible pour ce candidat.")

    latest_resume = sorted(candidate.resumes, key=lambda r: r.imported_at, reverse=True)[0]
    profile = latest_resume.extracted_profile
    if not profile:
        raise HTTPException(status_code=400, detail="Profil extrait introuvable pour ce candidat.")

    pdf_bytes = _generate_anonymized_pdf(profile)

    # Reply-To = email agence si renseigné (sinon SMTP_FROM par défaut)
    reply_to = None
    sender_display = ""
    if user.settings:
        reply_to = (user.settings.agency_email or "").strip() or None
        sender_display = (user.settings.company_name or "").strip()

    try:
        result = await send_email_smtp(
            user_settings=user.settings,
            subject=email_record.subject or "Proposition de candidat",
            body=email_record.body or "",
            recipients=email_record.recruiter_email,
            sender_display_name=sender_display,
            reply_to=reply_to,
            attachments=[("cv_anonymise.pdf", pdf_bytes, "pdf")],
        )
    except SmtpNotConfiguredError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SmtpSendError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Marquer envoyé + créer SentProposal
    now = datetime.now(timezone.utc)
    email_record.status = "sent"
    email_record.sent_at = now
    email_record.sent_message_id = result.get("message_id", "")[:500]

    # Récupérer la matching_result pour avoir le job_offer_id
    matching = await get_owned_matching(email_record.matching_result_id, db, user, with_offer=True)
    proposal = SentProposal(
        job_offer_id=matching.job_offer_id,
        candidate_id=candidate.id,
        email_id=email_record.id,
        sent_at=now,
    )
    db.add(proposal)
    await db.flush()
    await db.refresh(email_record)

    return {
        "status": "sent",
        "recipients": result["recipients"],
        "sent_at": now.isoformat(),
        "message_id": result.get("message_id", ""),
    }
