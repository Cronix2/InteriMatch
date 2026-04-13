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
