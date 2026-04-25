"""
InteriMatch AI - Service Hunter.io
Recherche d'emails professionnels via l'API Hunter.io
"""

import logging
import re
import unicodedata

import httpx

logger = logging.getLogger(__name__)

HUNTER_API_BASE = "https://api.hunter.io/v2"
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# ── Company-name cleaner ────────────────────────────────────────────
# France Travail company names often contain trailing noise:
#   "SYNERGIE - voir rce 26000799"  →  "SYNERGIE"
#   "ADECCO FRANCE - ref 12345"     →  "ADECCO FRANCE"
#   "ITINOVA"                       →  "ITINOVA"
#   "MANPOWER (LYON)"               →  "MANPOWER"
_COMPANY_NOISE_RE = re.compile(
    r"""
    \s*[-–—]\s*                   # dash separator
    (?:voir|ref|rce|réf|siret|siren|code|n°|id)
    .*                            # everything after
    """,
    re.IGNORECASE | re.VERBOSE,
)
_COMPANY_PARENS_RE = re.compile(r"\s*\(.*?\)\s*$")


def clean_company_name(raw: str) -> str:
    """
    Extract the real company name from a France Travail entreprise.nom field.
    Strips trailing references, parenthesized locations, extra whitespace.
    """
    if not raw:
        return ""
    name = raw.strip()
    # Remove trailing " - voir rce …", " - ref …", etc.
    name = _COMPANY_NOISE_RE.sub("", name)
    # Remove trailing parenthesized text like "(LYON)" or "(75010)"
    name = _COMPANY_PARENS_RE.sub("", name)
    # Collapse whitespace
    name = " ".join(name.split())
    return name.strip()


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

    Si le domaine fourni n'est pas un FQDN (ex: nom d'entreprise nu),
    plusieurs variantes TLD (.fr / .com / .net) sont essayées.
    """
    if not api_key or not domain:
        return None

    # Nettoyer le domaine (enlever http://, www., etc.)
    cleaned = domain.strip().lower()
    cleaned = re.sub(r"^https?://", "", cleaned)
    cleaned = re.sub(r"^www\.", "", cleaned)
    cleaned = cleaned.split("/")[0]

    # Si c'est déjà un FQDN, on l'utilise tel quel ; sinon on génère des candidats.
    if cleaned and "." in cleaned:
        domain_candidates = [cleaned]
    else:
        slug = _slug_company(cleaned)
        if not slug:
            return None
        domain_candidates = [f"{slug}.fr", f"{slug}.com"]

    for d in domain_candidates:
        result = await _hunter_lookup(api_key, d, first_name, last_name)
        if result:
            return result
    return None


async def _hunter_lookup(
    api_key: str,
    domain: str,
    first_name: str | None,
    last_name: str | None,
) -> dict | None:
    """Une tentative Hunter (finder + domain-search) pour un domaine donné."""
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
                            "domain": domain,
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
                    best = max(emails, key=lambda e: e.get("confidence", 0))
                    return {
                        "email": best["value"],
                        "confidence": best.get("confidence", 0),
                        "first_name": best.get("first_name", ""),
                        "last_name": best.get("last_name", ""),
                        "source": "hunter_domain",
                        "domain": domain,
                    }

    except Exception as e:
        logger.warning("Hunter.io API error on %s: %s", domain, e)

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


# HR and leadership departments / positions to prioritize
_HR_DEPARTMENTS = {"hr", "human resources", "executive", "management", "direction", "rh", "ressources humaines"}
_IMPORTANT_POSITIONS = {
    "ceo", "coo", "cfo", "cto", "directeur", "directrice", "dirigeant",
    "gérant", "gerante", "president", "présidente", "fondateur", "fondatrice",
    "responsable rh", "responsable recrutement", "drh", "recruitment",
    "recrutement", "talent", "hiring", "hr manager", "hr director",
    "recruitment manager", "head of hr", "chief",
}


async def fetch_company_contacts(
    api_key: str,
    domain: str | None = None,
    company_name: str | None = None,
    limit: int = 10,
) -> dict:
    """
    Fetch ALL contacts for a company via Hunter.io domain-search.
    Supports searching by domain OR by company name.
    Returns {"organization": str, "domain": str, "contacts": [{email, first_name, last_name, position, department, confidence, seniority, linkedin}]}
    """
    if not api_key or (not domain and not company_name):
        return {"organization": "", "domain": "", "contacts": []}

    # Clean domain if provided
    if domain:
        domain = domain.strip().lower()
        domain = re.sub(r"^https?://", "", domain)
        domain = re.sub(r"^www\.", "", domain)
        domain = domain.split("/")[0]
        if not domain or "." not in domain:
            domain = None

    if not domain and not company_name:
        return {"organization": "", "domain": "", "contacts": []}

    contacts: list[dict] = []
    organization = ""
    result_domain = domain or ""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Single API call — domain-search supports both ?domain= and ?company=
            url = f"{HUNTER_API_BASE}/domain-search"
            params: dict = {"api_key": api_key, "limit": limit}
            if domain:
                params["domain"] = domain
                logger.info("Hunter domain-search: domain=%s, limit=%s", domain, limit)
            else:
                params["company"] = company_name
                logger.info("Hunter domain-search: company=%s, limit=%s", company_name, limit)

            resp = await client.get(url, params=params)
            logger.info("Hunter response status: %s", resp.status_code)
            if resp.status_code == 200:
                resp_json = resp.json()
                data = resp_json.get("data", {})
                organization = data.get("organization", "")
                result_domain = data.get("domain", "") or result_domain
                emails_list = data.get("emails", [])
                logger.info(
                    "Hunter returned org=%s, domain=%s, %d emails",
                    organization, result_domain, len(emails_list),
                )
                for e in emails_list:
                    contacts.append({
                        "email": e.get("value", ""),
                        "first_name": e.get("first_name", ""),
                        "last_name": e.get("last_name", ""),
                        "position": e.get("position") or e.get("position_raw", ""),
                        "department": e.get("department", ""),
                        "confidence": e.get("confidence", 0),
                        "seniority": e.get("seniority", ""),
                        "linkedin": e.get("linkedin", ""),
                    })
            elif resp.status_code in (401, 403):
                logger.warning("Hunter.io auth failed (status %s): %s", resp.status_code, resp.text[:200])
            else:
                logger.warning("Hunter.io returned status %s for %s: %s", resp.status_code, domain or company_name, resp.text[:300])

    except Exception as e:
        logger.warning("Hunter.io company contacts error: %s", e)

    # Deduplicate by email
    seen = set()
    unique = []
    for c in contacts:
        if c["email"] and c["email"] not in seen:
            seen.add(c["email"])
            unique.append(c)

    # Sort: HR/management/executives first, then by confidence
    def sort_key(c: dict) -> tuple:
        dept = (c.get("department") or "").lower()
        pos = (c.get("position") or "").lower()
        seniority = (c.get("seniority") or "").lower()
        is_hr = dept in _HR_DEPARTMENTS
        is_important = any(kw in pos for kw in _IMPORTANT_POSITIONS) or seniority in ("senior", "executive", "c-level")
        return (not is_hr, not is_important, -c.get("confidence", 0))

    unique.sort(key=sort_key)
    return {"organization": organization, "domain": result_domain, "contacts": unique}


# ─────────────────────────────────────────────────────────────────────────
# Résolution de domaine — fallbacks gratuits quand Hunter ne trouve rien
# ─────────────────────────────────────────────────────────────────────────

# Mots à exclure des résultats DuckDuckGo (annuaires, réseaux sociaux, médias).
_DOMAIN_BLACKLIST = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "youtube.com", "wikipedia.org", "fr.wikipedia.org", "indeed.com", "indeed.fr",
    "pole-emploi.fr", "francetravail.fr", "welcometothejungle.com", "glassdoor.fr",
    "glassdoor.com", "viadeo.com", "societe.com", "verif.com", "infogreffe.fr",
    "pappers.fr", "manageo.fr", "kompass.com", "europages.fr", "leboncoin.fr",
    "hellowork.com", "meteojob.com", "monster.fr", "apec.fr", "jobijoba.com",
    "regionsjob.com", "youtube.fr", "yellowpages.com", "pagesjaunes.fr",
}

_FORM_DOMAIN_RE = re.compile(r"//([a-z0-9.-]+\.[a-z]{2,})", re.IGNORECASE)


def _strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )


def _slug_company(name: str) -> str:
    """Slug minuscule sans accent ni espaces (pour générer des candidats domaine)."""
    cleaned = _strip_accents(name).lower()
    cleaned = re.sub(r"[^a-z0-9]+", "", cleaned)
    return cleaned


def _candidate_domains(company: str) -> list[str]:
    """Génère des candidats de domaine plausibles pour une raison sociale."""
    slug = _slug_company(company)
    if not slug or len(slug) < 2:
        return []
    # Privilégier .fr (intérim FR) puis .com / .net
    return [f"{slug}.fr", f"{slug}.com", f"{slug}.net"]


async def _check_domain_alive(client: httpx.AsyncClient, domain: str) -> bool:
    """HEAD/GET rapide pour vérifier qu'un domaine répond (statut < 500)."""
    for scheme in ("https://", "http://"):
        try:
            resp = await client.head(
                f"{scheme}{domain}",
                follow_redirects=True,
                timeout=5,
            )
            if resp.status_code < 500:
                return True
        except Exception:
            continue
    return False


async def _duckduckgo_resolve(company: str) -> str | None:
    """
    Résout un nom d'entreprise en domaine via DuckDuckGo HTML (gratuit,
    pas de clé). Renvoie le premier domaine non-blacklisté trouvé.
    """
    if not company:
        return None
    query = f"{company} site officiel"
    try:
        async with httpx.AsyncClient(
            timeout=8,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                ),
            },
        ) as client:
            resp = await client.post(
                "https://duckduckgo.com/html/",
                data={"q": query},
                follow_redirects=True,
            )
            if resp.status_code != 200:
                return None
            text = resp.text
            for match in _FORM_DOMAIN_RE.finditer(text):
                raw = match.group(1).lower().lstrip("www.")
                if raw.startswith("duckduckgo.") or raw.endswith(".duckduckgo.com"):
                    continue
                if raw in _DOMAIN_BLACKLIST:
                    continue
                # Ignore les sous-domaines très longs (CDN, trackers)
                if raw.count(".") > 2:
                    continue
                return raw
    except Exception as e:
        logger.warning("DuckDuckGo resolve failed for '%s': %s", company, e)
    return None


async def resolve_company_domain(
    api_key: str | None,
    company_name: str,
) -> str | None:
    """
    Résout `company_name` en domaine en essayant dans l'ordre :
    1. Hunter.io domain-search ?company= (si clé fournie).
    2. Candidats heuristiques (slug.fr / .com / .net) avec ping HTTP.
    3. DuckDuckGo HTML scrape.
    Retourne le domaine ou None.
    """
    company_name = (company_name or "").strip()
    if not company_name:
        return None

    # 1) Hunter (si clé)
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{HUNTER_API_BASE}/domain-search",
                    params={
                        "company": company_name,
                        "api_key": api_key,
                        "limit": 1,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    domain = (data.get("domain") or "").strip().lower()
                    if domain and "." in domain:
                        return domain
        except Exception as e:
            logger.warning("Hunter resolve failed for '%s': %s", company_name, e)

    # 2) Heuristique slug + ping
    candidates = _candidate_domains(company_name)
    if candidates:
        try:
            async with httpx.AsyncClient(timeout=6) as client:
                for cand in candidates:
                    if await _check_domain_alive(client, cand):
                        logger.info(
                            "Domain resolved heuristically for '%s': %s",
                            company_name, cand,
                        )
                        return cand
        except Exception:
            pass

    # 3) Hunter Discover (fuzzy) avant DDG
    if api_key:
        discoveries = await hunter_discover_by_name(api_key, company_name, limit=1)
        if discoveries:
            logger.info(
                "Domain resolved via Hunter Discover for '%s': %s",
                company_name, discoveries[0]["domain"],
            )
            return discoveries[0]["domain"]

    # 4) DuckDuckGo (gratuit, sans clé)
    ddg = await _duckduckgo_resolve(company_name)
    if ddg:
        logger.info("Domain resolved via DuckDuckGo for '%s': %s", company_name, ddg)
        return ddg

    return None


async def fetch_company_contacts_robust(
    api_key: str,
    domain: str | None = None,
    company_name: str | None = None,
    limit: int = 10,
) -> dict:
    """
    Version robuste de `fetch_company_contacts` :
    - Si pas de `domain`, tente de le résoudre (Hunter → heuristique → DDG).
    - Réessaie une fois en cas d'échec d'identification du domaine.
    """
    if domain or not company_name:
        return await fetch_company_contacts(
            api_key=api_key, domain=domain, company_name=company_name, limit=limit,
        )

    # Essai 1 : laisser Hunter chercher par company_name
    first = await fetch_company_contacts(
        api_key=api_key, domain=None, company_name=company_name, limit=limit,
    )
    if first.get("domain") and first.get("contacts"):
        return first

    # Essai 2 : résoudre le domaine via fallbacks puis interroger Hunter
    resolved = await resolve_company_domain(api_key, company_name)
    if resolved:
        retry = await fetch_company_contacts(
            api_key=api_key, domain=resolved, company_name=None, limit=limit,
        )
        if retry.get("contacts"):
            return retry
        # Pas de contacts mais domaine résolu : remonter quand même
        return {
            "organization": first.get("organization") or company_name,
            "domain": resolved,
            "contacts": [],
        }

    return first


# ─────────────────────────────────────────────────────────────────────────
# Hunter Discover — recherche fuzzy d'entreprises par nom
# ─────────────────────────────────────────────────────────────────────────

async def hunter_discover_by_name(api_key: str, company_name: str, limit: int = 5) -> list[dict]:
    """
    Hunter Discover (POST /v2/discover) : recherche fuzzy d'entreprises par nom.
    Retourne une liste {organization, domain, industry, country} triée par
    pertinence — utile quand domain-search ne trouve rien (entreprises peu connues).
    """
    if not api_key or not company_name:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{HUNTER_API_BASE}/discover",
                params={"api_key": api_key},
                json={
                    "query": {"organization": {"value": company_name}},
                    "limit": limit,
                },
            )
            if resp.status_code != 200:
                logger.info(
                    "Hunter Discover %s for '%s': %s",
                    resp.status_code, company_name, resp.text[:200],
                )
                return []
            data = resp.json().get("data", {})
            companies = data.get("companies") or data.get("organizations") or []
            results = []
            for c in companies:
                domain = (c.get("domain") or "").strip().lower()
                if not domain or "." not in domain:
                    continue
                if domain in _DOMAIN_BLACKLIST:
                    continue
                results.append({
                    "organization": c.get("organization") or c.get("name") or "",
                    "domain": domain,
                    "industry": c.get("industry", ""),
                    "country": c.get("country", ""),
                })
            return results
    except Exception as e:
        logger.warning("Hunter Discover failed for '%s': %s", company_name, e)
        return []


# ─────────────────────────────────────────────────────────────────────────
# Email Verifier — vérifier qu'une adresse précise existe vraiment
# ─────────────────────────────────────────────────────────────────────────

async def verify_email(api_key: str, email: str) -> dict | None:
    """
    Hunter Email Verifier (/email-verifier).
    Retourne {"email", "status", "result", "score"} ou None.
    `status` ∈ {valid, invalid, accept_all, webmail, disposable, unknown}.
    On considère acceptables : valid, accept_all, webmail (avec score >= 50).
    """
    if not api_key or not email:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{HUNTER_API_BASE}/email-verifier",
                params={"email": email, "api_key": api_key},
            )
            if resp.status_code != 200:
                return None
            data = resp.json().get("data", {})
            return {
                "email": data.get("email", email),
                "status": data.get("status", ""),
                "result": data.get("result", ""),
                "score": int(data.get("score") or 0),
            }
    except Exception as e:
        logger.info("Hunter verify failed for '%s': %s", email, e)
        return None


# Patterns d'emails RH/recrutement classiques (FR) testés en fallback
_GENERIC_PATTERNS = [
    ("recrutement", "RH"),
    ("rh",          "RH"),
    ("candidatures","RH"),
    ("candidature", "RH"),
    ("emploi",      "RH"),
    ("jobs",        "RH"),
    ("careers",     "RH"),
    ("hr",          "RH"),
    ("contact",     "Contact général"),
    ("info",        "Contact général"),
    ("direction",   "Direction"),
    ("accueil",     "Accueil"),
]


async def find_pattern_emails(api_key: str, domain: str, max_results: int = 5) -> list[dict]:
    """
    Génère des candidats `motif@domaine` (contact@, rh@, recrutement@…)
    et les vérifie via Hunter Email Verifier. Retourne uniquement ceux jugés
    valides ou catch-all.
    """
    if not api_key or not domain:
        return []

    # Limiter le nombre de vérifications pour ne pas griller les crédits Hunter
    candidates = _GENERIC_PATTERNS[: max(max_results * 2, 6)]

    async def _try(local: str, dept: str) -> dict | None:
        email = f"{local}@{domain}"
        result = await verify_email(api_key, email)
        if not result:
            return None
        status = (result.get("status") or "").lower()
        score = result.get("score", 0)
        # Garder valid + accept_all (catch-all) avec score raisonnable
        if status == "valid" or (status == "accept_all" and score >= 40):
            return {
                "email": email,
                "first_name": "",
                "last_name": "",
                "position": dept,
                "department": dept,
                "confidence": score or (90 if status == "valid" else 50),
                "seniority": "",
                "linkedin": "",
                "source": "pattern",
            }
        return None

    import asyncio as _asyncio
    results = await _asyncio.gather(
        *[_try(local, dept) for local, dept in candidates],
        return_exceptions=True,
    )
    valid = [r for r in results if isinstance(r, dict)]
    # Trier par confidence puis par ordre des patterns (recrutement avant contact)
    valid.sort(key=lambda c: -c.get("confidence", 0))
    return valid[:max_results]


async def fetch_company_contacts_full(
    api_key: str,
    domain: str | None = None,
    company_name: str | None = None,
    limit: int = 10,
) -> dict:
    """
    Stratégie complète pour trouver des contacts :
    1. Hunter domain-search par domaine ou nom (fetch_company_contacts_robust)
    2. Si toujours pas de domaine → Hunter Discover (recherche fuzzy)
    3. Si domaine trouvé mais aucun contact → patterns vérifiés (contact@, rh@…)
    Retourne {"organization", "domain", "contacts": [...]}
    """
    base = await fetch_company_contacts_robust(
        api_key=api_key, domain=domain, company_name=company_name, limit=limit,
    )
    if base.get("contacts"):
        # On a déjà des contacts — on peut compléter avec patterns si peu nombreux
        if len(base["contacts"]) < 3 and base.get("domain"):
            extra = await find_pattern_emails(api_key, base["domain"], max_results=5)
            seen = {c["email"] for c in base["contacts"]}
            for c in extra:
                if c["email"] not in seen:
                    base["contacts"].append(c)
        return base

    resolved_domain = base.get("domain") or ""

    # 2) Hunter Discover si toujours pas de domaine
    if not resolved_domain and company_name:
        discoveries = await hunter_discover_by_name(api_key, company_name, limit=3)
        for cand in discoveries:
            retry = await fetch_company_contacts(
                api_key=api_key, domain=cand["domain"], company_name=None, limit=limit,
            )
            if retry.get("contacts"):
                return retry
            # Domaine trouvé mais pas de contacts → on garde et tente patterns
            if not resolved_domain:
                resolved_domain = cand["domain"]
                base["organization"] = base.get("organization") or cand.get("organization") or ""

    # 3) Patterns sur le domaine résolu
    if resolved_domain:
        patterns = await find_pattern_emails(api_key, resolved_domain, max_results=5)
        if patterns:
            return {
                "organization": base.get("organization") or company_name or "",
                "domain": resolved_domain,
                "contacts": patterns,
            }
        return {
            "organization": base.get("organization") or company_name or "",
            "domain": resolved_domain,
            "contacts": [],
        }

    return base

