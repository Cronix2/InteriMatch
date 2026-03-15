"""
InteriMatch AI - Service de parsing de CV (PDF / DOCX)
Extrait le texte brut puis appelle le LLM pour structurer les données.
"""

import io
from pathlib import Path

import pdfplumber
from docx import Document

from app.services.ai_service import extract_cv_profile


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrait le texte d'un fichier PDF."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extrait le texte d'un fichier DOCX."""
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())


def extract_text(file_bytes: bytes, file_name: str) -> str:
    """Détecte le format et extrait le texte brut."""
    suffix = Path(file_name).suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Format de fichier non supporté : {suffix}. Formats acceptés : PDF, DOCX")


async def parse_cv(file_bytes: bytes, file_name: str) -> dict:
    """
    Pipeline complet de parsing CV :
    1. Extraction du texte brut
    2. Extraction structurée via IA (LangChain)
    
    Retourne : {"raw_text": str, "profile": dict}
    """
    raw_text = extract_text(file_bytes, file_name)
    if not raw_text.strip():
        raise ValueError("Impossible d'extraire du texte depuis ce fichier. Le document est peut-être vide ou scanné.")

    profile = await extract_cv_profile(raw_text)

    return {
        "raw_text": raw_text,
        "profile": profile,
    }
