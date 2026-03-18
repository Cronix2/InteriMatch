"""
InteriMatch AI - Service IA via LangChain (OpenAI-compatible)
Centralise tous les appels au LLM.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.core.config import get_settings

settings = get_settings()


def get_llm() -> ChatOpenAI:
    """Instancie le client LLM OpenAI-compatible via LangChain."""
    return ChatOpenAI(
        model=settings.ai_model,
        base_url=settings.ai_server_url,
        api_key=settings.ai_api_key or "not-needed",
        temperature=settings.ai_temperature,
        max_tokens=settings.ai_max_tokens,
        request_timeout=120,
    )


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
  "desired_job_titles": ["intitulé poste recherché 1", ...]
}}"""),
    ("human", "Voici le texte brut du CV :\n\n{cv_text}")
])


async def extract_cv_profile(cv_text: str) -> dict:
    """Extrait les informations structurées d'un CV via le LLM."""
    llm = get_llm()
    chain = CV_EXTRACTION_PROMPT | llm | JsonOutputParser()
    return await chain.ainvoke({"cv_text": cv_text})


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


async def compute_ai_matching(candidate_profile: str, job_offer: str) -> dict:
    """Calcule le score de matching candidat/offre via le LLM."""
    llm = get_llm()
    chain = MATCHING_PROMPT | llm | JsonOutputParser()
    return await chain.ainvoke({
        "candidate_profile": candidate_profile,
        "job_offer": job_offer,
    })


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
EXPLICATION DU MATCHING : {match_explanation}""")
])


async def generate_email(
    candidate_profile: str,
    job_title: str,
    company_name: str,
    job_location: str,
    job_description: str,
    match_score: float,
    match_explanation: str,
) -> dict:
    """Génère un mail professionnel de proposition de candidat."""
    llm = get_llm()
    chain = EMAIL_GENERATION_PROMPT | llm | JsonOutputParser()
    return await chain.ainvoke({
        "candidate_profile": candidate_profile,
        "job_title": job_title,
        "company_name": company_name,
        "job_location": job_location,
        "job_description": job_description,
        "match_score": str(match_score),
        "match_explanation": match_explanation,
    })
