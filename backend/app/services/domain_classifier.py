"""
InteriMatch AI - Classification du domaine d'activité d'un CV.

Vocabulaire contrôlé aligné sur les grandes familles ROME (intérim FR).
Sert à :
1. Imposer un terme normalisé au LLM (CV_EXTRACTION_PROMPT).
2. Corriger / valider la sortie LLM (`normalize_domain`).
3. Fournir un fallback déterministe par mots-clés si le LLM répond mal
   (`infer_domain_from_text`).
"""

from __future__ import annotations

import re
import unicodedata

# ──────────────────────────────────────────────────────────────────────────
# Vocabulaire fermé. Toujours ajouter ici avant d'utiliser une nouvelle
# valeur ailleurs dans le code.
# ──────────────────────────────────────────────────────────────────────────
DOMAINS: tuple[str, ...] = (
    "informatique",
    "batiment",
    "logistique_transport",
    "restauration_hotellerie",
    "industrie",
    "commerce_vente",
    "sante",
    "administration",
    "comptabilite_finance",
    "electricite",
    "mecanique",
    "agriculture",
    "education",
    "beaute",
    "securite",
    "social",
    "artisanat",
    "communication_marketing",
    "juridique",
    "autre",
)

DOMAIN_LABELS_FR: dict[str, str] = {
    "informatique": "Informatique / Numérique",
    "batiment": "Bâtiment / BTP",
    "logistique_transport": "Logistique / Transport",
    "restauration_hotellerie": "Restauration / Hôtellerie",
    "industrie": "Industrie / Production",
    "commerce_vente": "Commerce / Vente",
    "sante": "Santé / Médical",
    "administration": "Administration / Secrétariat",
    "comptabilite_finance": "Comptabilité / Finance",
    "electricite": "Électricité",
    "mecanique": "Mécanique",
    "agriculture": "Agriculture",
    "education": "Éducation / Formation",
    "beaute": "Beauté / Bien-être",
    "securite": "Sécurité",
    "social": "Social / Aide à la personne",
    "artisanat": "Artisanat",
    "communication_marketing": "Communication / Marketing",
    "juridique": "Juridique",
    "autre": "Autre",
}

# ──────────────────────────────────────────────────────────────────────────
# Mots-clés par domaine (lowercase, sans accent). Utilisés à la fois pour
# corriger la valeur LLM et pour deviner depuis du texte brut.
# ──────────────────────────────────────────────────────────────────────────
_KEYWORDS: dict[str, tuple[str, ...]] = {
    "informatique": (
        "informatique", "developpeur", "developpeuse", "devops", "fullstack", "full-stack",
        "backend", "frontend", "logiciel", "software", "python", "java ", "javascript",
        "typescript", "react", "node", "angular", "vue", "sql", "cloud", "aws", "azure",
        "kubernetes", "docker", "linux", "cybersecur", "data engineer", "data scien",
        "machine learning", "intelligence artificielle", " it ", "tech lead", "sysadmin",
        "administrateur systeme", "reseau", "support informatique", "helpdesk", "web",
    ),
    "batiment": (
        "batiment", "btp", "macon", "couvreur", "charpentier", "plaquiste", "carreleur",
        "peintre en batiment", "platrier", "menuisier", "gros oeuvre", "second oeuvre",
        "chantier", "conducteur de travaux", "chef de chantier", "terrassement", "renovation",
        "isolation", "couvreur", "etancheite",
    ),
    "logistique_transport": (
        "logistique", "cariste", "magasinier", "preparateur de commandes",
        "preparatrice de commandes", "manutentionnaire", "chauffeur", "chauffeuse",
        "conducteur poids lourd", "conducteur spl", "conductrice spl", "transport",
        "livraison", "livreur", "livreuse", "fenwick", "caces", "supply chain", "entrepot",
        "expedition", "deplacement", "fret", "routier",
    ),
    "restauration_hotellerie": (
        "restauration", "cuisinier", "cuisiniere", "commis de cuisine", "chef de partie",
        "second de cuisine", "plongeur", "serveur", "serveuse", "barman", "barmaid",
        "hotellerie", "hotel", "reception hotel", "femme de chambre", "valet de chambre",
        "gouvernante", "boulanger", "patissier", "patissiere", "boucher", "boucherie",
        "traiteur", "pizzaiolo",
    ),
    "industrie": (
        "industrie", "operateur de production", "operatrice de production",
        "agent de production", "conducteur de ligne", "conductrice de ligne",
        "soudeur", "soudeuse", "chaudronnier", "tourneur", "fraiseur", "ajusteur",
        "regleur", "controle qualite", "metallurgie", "plasturgie", "agroalimentaire",
        "usine", "atelier", "automatisme",
    ),
    "commerce_vente": (
        "commerce", "vente", "vendeur", "vendeuse", "conseiller commercial",
        "conseillere commerciale", "responsable de magasin", "caissier", "caissiere",
        "merchandising", "televendeur", "televendeuse", "negociateur", "business developer",
        "account manager", "retail", "boutique", "grande distribution",
    ),
    "sante": (
        "sante", "medecin", "infirmier", "infirmiere", "ide ", "aide soignant",
        "aide-soignant", "aide-soignante", "kinesitherapeute", "kine ", "pharmacien",
        "pharmacienne", "preparateur en pharmacie", "dentiste", "sage femme", "sage-femme",
        "auxiliaire de puericulture", "ambulancier", "ambulanciere", "hospitalier",
        "ehpad", "clinique", "hopital",
    ),
    "administration": (
        "administration", "secretaire", "assistante de direction", "assistant de direction",
        "assistant administratif", "assistante administrative", "agent administratif",
        "accueil", "standardiste", "office manager", "back office", "saisie",
    ),
    "comptabilite_finance": (
        "comptable", "comptabilite", "controleur de gestion", "auditeur", "auditrice",
        "assistant comptable", "assistante comptable", "fiscaliste", "tresorerie",
        "paie", "gestionnaire de paie", "finance", "credit manager",
    ),
    "electricite": (
        "electricien", "electricienne", "electricite", "electrotechnique",
        "electrotechnicien", "monteur cableur", "monteuse cableuse", "installateur electrique",
        "habilitation electrique", "tableautier",
    ),
    "mecanique": (
        "mecanicien", "mecanicienne", "mecanique", "garagiste", "carrossier", "carrossiere",
        "peintre carrosserie", "diagnostic auto", "poids lourds mecanique",
    ),
    "agriculture": (
        "agriculture", "agricole", "ouvrier agricole", "viticulture", "viticole",
        "elevage", "eleveur", "marachage", "horticulture", "paysagiste", "espaces verts",
        "tractoriste", "vendangeur", "vendangeuse",
    ),
    "education": (
        "education", "enseignant", "enseignante", "professeur", "instituteur",
        "institutrice", "formateur", "formatrice", "animateur", "animatrice",
        "educateur sportif", "moniteur", "monitrice",
    ),
    "beaute": (
        "coiffeur", "coiffeuse", "estheticienne", "estheticien", "esthetique",
        "manucure", "spa praticien", "spa praticienne", "barber", "prothesiste ongulaire",
    ),
    "securite": (
        "agent de securite", "agente de securite", "securite incendie", "ssiap",
        "vigile", "garde du corps", "rondier", "rondiere", "maitre chien", "convoyeur de fonds",
    ),
    "social": (
        "social", "auxiliaire de vie", "aide a domicile", "educateur specialise",
        "educatrice specialisee", "assistant social", "assistante sociale", "ame ",
        "moniteur educateur", "monitrice educatrice", "tisf",
    ),
    "artisanat": (
        "artisan", "ebeniste", "tailleur de pierre", "ferronnier", "bijoutier",
        "horloger", "couturier", "couturiere", "potier", "vitrier",
    ),
    "communication_marketing": (
        "communication", "marketing", "community manager", "graphiste", "infographiste",
        "chef de projet marketing", "seo", "sea", "redacteur web", "redactrice web",
        "content manager", "designer ux", "designer ui",
    ),
    "juridique": (
        "juridique", "juriste", "avocat", "avocate", "paralegal", "notaire", "clerc",
        "huissier", "compliance", "conformite",
    ),
}

# Domaines proposés à l'IA dans le prompt (sans "autre" qui sert d'échappatoire interne)
PROMPT_VOCABULARY = ", ".join(d for d in DOMAINS if d != "autre")

_DOMAIN_SET = set(DOMAINS)


def _strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )


def _normalize_token(value: str) -> str:
    """Retourne une version lowercase, sans accent, espaces/tirets/slashes -> _."""
    if not value:
        return ""
    cleaned = _strip_accents(value).lower().strip()
    cleaned = re.sub(r"[\s/\\,;|]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("_")


# Synonymes courants -> domaine canonique (cas LLM qui dérive)
_ALIAS: dict[str, str] = {
    "it": "informatique",
    "tech": "informatique",
    "developpement": "informatique",
    "developpement_logiciel": "informatique",
    "numerique": "informatique",
    "software": "informatique",
    "btp": "batiment",
    "construction": "batiment",
    "travaux_publics": "batiment",
    "transport": "logistique_transport",
    "logistique": "logistique_transport",
    "supply_chain": "logistique_transport",
    "restauration": "restauration_hotellerie",
    "hotellerie": "restauration_hotellerie",
    "cuisine": "restauration_hotellerie",
    "production": "industrie",
    "manufacturing": "industrie",
    "usinage": "industrie",
    "vente": "commerce_vente",
    "commerce": "commerce_vente",
    "retail": "commerce_vente",
    "medical": "sante",
    "paramedical": "sante",
    "hospitalier": "sante",
    "secretariat": "administration",
    "comptabilite": "comptabilite_finance",
    "finance": "comptabilite_finance",
    "paie": "comptabilite_finance",
    "electricien": "electricite",
    "electrotechnique": "electricite",
    "mecanicien": "mecanique",
    "automobile": "mecanique",
    "agricole": "agriculture",
    "espaces_verts": "agriculture",
    "enseignement": "education",
    "formation": "education",
    "esthetique": "beaute",
    "coiffure": "beaute",
    "bien_etre": "beaute",
    "surveillance": "securite",
    "gardiennage": "securite",
    "aide_a_la_personne": "social",
    "auxiliaire_de_vie": "social",
    "marketing": "communication_marketing",
    "communication": "communication_marketing",
    "droit": "juridique",
    "juriste": "juridique",
}


def normalize_domain(value: str | None) -> str | None:
    """
    Mappe une valeur libre (LLM) vers un terme du vocabulaire contrôlé.
    Retourne None si l'entrée est vide.
    """
    if not value:
        return None
    token = _normalize_token(value)
    if not token:
        return None
    if token in _DOMAIN_SET:
        return token
    if token in _ALIAS:
        return _ALIAS[token]
    # Le LLM a parfois renvoyé plusieurs mots ("informatique / dev")
    for part in token.split("_"):
        if part in _DOMAIN_SET:
            return part
        if part in _ALIAS:
            return _ALIAS[part]
    # Match par préfixe
    for d in DOMAINS:
        if token.startswith(d):
            return d
    return None


def infer_domain_from_text(*texts: str) -> str | None:
    """
    Devine un domaine en comptant les mots-clés présents dans les textes
    (titre poste recherché, résumé, expériences). Renvoie None si aucun
    mot-clé n'est trouvé.
    """
    blob = " ".join(t for t in texts if t)
    if not blob:
        return None
    haystack = " " + _strip_accents(blob).lower() + " "

    scores: dict[str, int] = {}
    for domain, keywords in _KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in haystack:
                score += 1
        if score:
            scores[domain] = score

    if not scores:
        return None
    # Prendre le domaine au score max ; tie-break sur l'ordre déclaré dans DOMAINS
    best = max(scores.items(), key=lambda kv: (kv[1], -DOMAINS.index(kv[0])))
    return best[0]


def resolve_profile_domain(profile_data: dict) -> str | None:
    """
    Pipeline complet : normalise la valeur LLM, sinon devine depuis le texte
    du profil, sinon retourne None.
    """
    raw = profile_data.get("professional_domain")
    canonical = normalize_domain(raw) if raw else None
    if canonical and canonical != "autre":
        return canonical

    # Construire un texte représentatif pour le fallback déterministe
    parts: list[str] = []
    summary = profile_data.get("profile_summary")
    if summary:
        parts.append(str(summary))

    titles = profile_data.get("desired_job_titles") or []
    if titles:
        parts.append(" ".join(str(t) for t in titles))

    skills = profile_data.get("skills") or []
    if skills:
        parts.append(" ".join(str(s) for s in skills))

    experiences = profile_data.get("experiences") or []
    for exp in experiences:
        if isinstance(exp, dict):
            parts.append(" ".join(
                str(exp.get(k, "")) for k in ("title", "company", "description")
            ))

    inferred = infer_domain_from_text(*parts)
    if inferred:
        return inferred

    # Si LLM avait répondu "autre" ou un terme inconnu, on garde "autre"
    if canonical == "autre":
        return "autre"
    return None
