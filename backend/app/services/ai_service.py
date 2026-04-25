"""
InteriMatch AI - Service IA via LangChain (OpenAI-compatible)
Centralise tous les appels au LLM.
"""

import time
import logging
import uuid
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.core.config import get_settings
from app.core.database import async_session
from app.models.models import ApiUsageLog
from app.services.domain_classifier import PROMPT_VOCABULARY, resolve_profile_domain
from app.services.ai_providers import resolve_provider

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class ApiUsageEntry:
    service: str
    action: str
    latency_ms: int
    success: bool
    error_message: str | None = None
    tokens_input: int = 0
    tokens_output: int = 0
    user_id: str | None = None


def get_llm(user_settings=None) -> ChatOpenAI:
    """Instancie le client LLM OpenAI-compatible via LangChain.

    Priorité :
    1. user_settings : provider/base_url/api_key/model de l'utilisateur connecté
    2. settings (env) : valeurs globales `.env` (AI_PROVIDER, AI_API_KEY, ...)

    Si l'utilisateur a sélectionné un provider connu (groq, mistral, ...) sans
    fournir d'URL, le preset est appliqué automatiquement.
    """
    if user_settings is not None:
        provider = (
            getattr(user_settings, "ai_provider", None) or settings.ai_provider
        )
        api_key = (
            getattr(user_settings, "ai_api_key", None) or settings.ai_api_key
        )
        base_url = (
            getattr(user_settings, "ai_base_url", None) or settings.ai_server_url
        )
        model = (
            getattr(user_settings, "ai_model", None) or settings.ai_model
        )
        temperature = (
            user_settings.ai_temperature
            if getattr(user_settings, "ai_temperature", None) is not None
            else settings.ai_temperature
        )
    else:
        provider = settings.ai_provider
        api_key = settings.ai_api_key
        base_url = settings.ai_server_url
        model = settings.ai_model
        temperature = settings.ai_temperature

    eff_base_url, eff_key, eff_model = resolve_provider(
        provider, base_url=base_url, api_key=api_key, model=model,
    )

    return ChatOpenAI(
        model=eff_model,
        base_url=eff_base_url,
        api_key=eff_key,
        temperature=temperature,
        max_tokens=settings.ai_max_tokens,
        request_timeout=120,
    )


async def _log_api_usage(entry: ApiUsageEntry):
    """Enregistre une utilisation d'API dans la base."""
    try:
        estimated_cost = (entry.tokens_input * 0.00001) + (entry.tokens_output * 0.00003)
        async with async_session() as db:
            log = ApiUsageLog(
                user_id=uuid.UUID(entry.user_id) if entry.user_id else None,
                service=entry.service,
                action=entry.action,
                tokens_input=entry.tokens_input,
                tokens_output=entry.tokens_output,
                latency_ms=entry.latency_ms,
                estimated_cost=round(estimated_cost, 6),
                success=entry.success,
                error_message=entry.error_message,
            )
            db.add(log)
            await db.commit()
    except Exception as e:
        logger.warning("Échec log API usage: %s", e)


# ─── Extraction de profil CV ────────────────────────────────────────────────

CV_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un expert en extraction d'informations de CV pour le secteur de l'intérim en France.
À partir du texte brut d'un CV, extrais les informations suivantes au format JSON strict.

Réponds UNIQUEMENT avec le JSON, sans texte avant ni après.

Format attendu :
{{
  "first_name": "string ou null",
  "last_name": "string ou null",
  "email": "string ou null",
  "phone": "string ou null",
  "location": "string ou null",
  "availability": "string ou null",
  "skills": ["compétence1", "compétence2", ...],
  "experiences": [
    {{"title": "intitulé", "company": "entreprise", "duration": "durée", "description": "description courte"}}
  ],
  "education": [
    {{"diploma": "diplôme", "school": "établissement", "year": "année"}}
  ],
  "certifications": ["cert1", ...],
  "languages": ["Français", "Anglais", ...],
  "mobility": "zone de mobilité ou null",
  "profile_summary": "résumé professionnel en 2-3 phrases",
  "years_of_experience": nombre_entier_ou_null,
  "desired_job_titles": ["intitulé poste recherché 1", ...],
  "professional_domain": "UNE seule valeur, choisie strictement dans cette liste : {vocabulary}. Si aucun ne correspond exactement, renvoie 'autre'."
}}"""),
    ("human", "Voici le texte brut du CV :\n\n{cv_text}")
])


async def extract_cv_profile(cv_text: str, user_id: str | None = None, user_settings=None) -> dict:
    """Extrait les informations structurées d'un CV via le LLM."""
    llm = get_llm(user_settings)
    chain = CV_EXTRACTION_PROMPT | llm | JsonOutputParser()
    start = time.monotonic()
    try:
        result = await chain.ainvoke({"cv_text": cv_text, "vocabulary": PROMPT_VOCABULARY})
        latency = int((time.monotonic() - start) * 1000)
        tokens_in = len(cv_text) // 4
        await _log_api_usage(ApiUsageEntry("ai", "extract_cv", latency, True, tokens_input=tokens_in, tokens_output=500, user_id=user_id))
        # Normalisation + fallback déterministe (vocabulaire contrôlé)
        if isinstance(result, dict):
            try:
                result["professional_domain"] = resolve_profile_domain(result)
            except Exception as exc:  # pragma: no cover - safety net
                logger.warning("resolve_profile_domain failed: %s", exc)
        return result
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        await _log_api_usage(ApiUsageEntry("ai", "extract_cv", latency, False, error_message=str(e)[:200], user_id=user_id))
        raise


# ─── Matching scoring assisté IA ────────────────────────────────────────────

MATCHING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un expert en recrutement intérimaire en France.
Analyse la compatibilité entre le profil candidat et l'offre d'emploi.

Donne un score de 0 à 100 pour chaque critère et une explication globale.
Réponds UNIQUEMENT en JSON strict :

{{
  "global_score": float (0-100),
  "skills_score": float (0-100),
  "experience_score": float (0-100),
  "location_score": float (0-100),
  "education_score": float (0-100),
  "job_title_score": float (0-100),
  "explanation": "Explication concise du matching en français"
}}

Pondération : compétences 35%, expérience 25%, intitulé métier 20%, localisation 10%, diplômes 10%."""),
    ("human", """PROFIL CANDIDAT :
{candidate_profile}

OFFRE D'EMPLOI :
{job_offer}""")
])


async def compute_ai_matching(candidate_profile: str, job_offer: str, user_id: str | None = None, user_settings=None) -> dict:
    """Calcule le score de matching candidat/offre via le LLM."""
    llm = get_llm(user_settings)
    chain = MATCHING_PROMPT | llm | JsonOutputParser()
    start = time.monotonic()
    try:
        result = await chain.ainvoke({
            "candidate_profile": candidate_profile,
            "job_offer": job_offer,
        })
        latency = int((time.monotonic() - start) * 1000)
        tokens_in = (len(candidate_profile) + len(job_offer)) // 4
        await _log_api_usage(ApiUsageEntry("ai", "matching", latency, True, tokens_input=tokens_in, tokens_output=300, user_id=user_id))
        return result
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        await _log_api_usage(ApiUsageEntry("ai", "matching", latency, False, error_message=str(e)[:200], user_id=user_id))
        raise


# ─── Génération de mail ─────────────────────────────────────────────────────

EMAIL_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un rédacteur professionnel spécialisé dans le recrutement intérimaire en France.
Rédige un mail professionnel à destination de l'entreprise qui a publié l'offre d'emploi.
Le mail est envoyé par un chargé de recrutement d'une agence d'intérim pour proposer un candidat.

RÈGLES STRICTES :
- NE JAMAIS mentionner le nom, prénom, email, téléphone ou toute information d'identité du candidat.
- Parler du candidat de manière anonyme : "notre candidat", "le profil que nous vous proposons", etc.
- Le but est que l'entreprise passe par notre agence d'intérim pour rencontrer le candidat.
- Inclure un appel à l'action invitant l'entreprise à nous contacter pour organiser un entretien.
- Ton professionnel et courtois.
- Factuel, basé uniquement sur les compétences et expériences fournies.
- Pas d'invention ni d'hallucination.
- Utiliser les coordonnées de l'agence fournies pour la signature (si disponibles).
- Si un modèle d'email est fourni, s'en inspirer pour la structure et le ton.
- Structure : objet du mail, corps du mail.

Réponds en JSON strict :
{{
  "subject": "Objet du mail",
  "body": "Corps complet du mail"
}}"""),
    ("human", """COMPÉTENCES ET EXPÉRIENCE DU CANDIDAT (anonyme) :
{candidate_profile}

OFFRE D'EMPLOI :
Poste : {job_title}
Entreprise : {company_name}
Lieu : {job_location}
Description : {job_description}

SCORE DE MATCHING : {match_score}/100
EXPLICATION DU MATCHING : {match_explanation}

COORDONNÉES DE L'AGENCE :
{agency_info}

MODÈLE D'EMAIL À SUIVRE :
{email_template}""")
])


async def generate_email(
    candidate_profile: str,
    job_title: str,
    company_name: str,
    job_location: str,
    job_description: str,
    match_score: float,
    match_explanation: str,
    agency_info: str = "",
    email_template: str = "",
    user_id: str | None = None,
    user_settings=None,
) -> dict:
    """Génère un mail professionnel de proposition de candidat."""
    llm = get_llm(user_settings)
    chain = EMAIL_GENERATION_PROMPT | llm | JsonOutputParser()
    start = time.monotonic()
    try:
        result = await chain.ainvoke({
            "candidate_profile": candidate_profile,
            "job_title": job_title,
            "company_name": company_name,
            "job_location": job_location,
            "job_description": job_description,
            "match_score": str(match_score),
            "match_explanation": match_explanation,
            "agency_info": agency_info or "(non renseignées)",
            "email_template": email_template or "(utiliser le format par défaut)",
        })
        latency = int((time.monotonic() - start) * 1000)
        total_input = len(candidate_profile) + len(job_description) + len(agency_info) + len(email_template)
        tokens_in = total_input // 4
        await _log_api_usage(ApiUsageEntry("ai", "generate_email", latency, True, tokens_input=tokens_in, tokens_output=600, user_id=user_id))
        return result
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        await _log_api_usage(ApiUsageEntry("ai", "generate_email", latency, False, error_message=str(e)[:200], user_id=user_id))
        raise
