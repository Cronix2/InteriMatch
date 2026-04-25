"""
InteriMatch AI - Presets de fournisseurs LLM OpenAI-compatibles.

Tous ces providers exposent une API compatible OpenAI Chat Completions
et fonctionnent donc avec `langchain_openai.ChatOpenAI`.

Choix de l'utilisateur :
- `custom` : aucun preset appliqué — l'URL et la clé saisies sont utilisées telles
  quelles. Idéal pour serveur LLM interne (ex: Orange Liveintelligence) ou tout
  endpoint OpenAI-compatible non listé.
- `groq`, `openrouter`, `mistral`, `together` : SaaS gratuits ou freemium.
- `ollama` : serveur local (Docker / binaire) — aucune clé requise.
- `openai` : OpenAI officiel.
"""

from __future__ import annotations

from typing import TypedDict


class ProviderPreset(TypedDict):
    base_url: str
    requires_key: bool
    default_model: str
    label: str
    docs: str


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "requires_key": True,
        "default_model": "llama-3.3-70b-versatile",
        "label": "Groq (gratuit, ultra-rapide)",
        "docs": "https://console.groq.com",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "requires_key": True,
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
        "label": "OpenRouter (modèles gratuits dispo)",
        "docs": "https://openrouter.ai/keys",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "requires_key": True,
        "default_model": "mistral-small-latest",
        "label": "Mistral AI (FR, freemium)",
        "docs": "https://console.mistral.ai",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "requires_key": True,
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "label": "Together AI",
        "docs": "https://api.together.xyz/settings/api-keys",
    },
    "ollama": {
        "base_url": "http://ollama:11434/v1",
        "requires_key": False,
        "default_model": "qwen2.5:7b",
        "label": "Ollama (local Docker, 100% gratuit)",
        "docs": "https://ollama.com",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "requires_key": True,
        "default_model": "gpt-4o-mini",
        "label": "OpenAI",
        "docs": "https://platform.openai.com/api-keys",
    },
    "custom": {
        "base_url": "",
        "requires_key": False,
        "default_model": "",
        "label": "Personnalisé (OpenAI-compatible)",
        "docs": "",
    },
}

ALLOWED_PROVIDERS: frozenset[str] = frozenset(PROVIDER_PRESETS.keys())


def resolve_provider(
    provider: str | None,
    *,
    base_url: str | None,
    api_key: str | None,
    model: str | None,
) -> tuple[str, str, str]:
    """
    À partir des préférences (provider + override base_url/key/model),
    résout les valeurs effectives à utiliser pour instancier `ChatOpenAI`.

    Règles :
    - Si `provider` est inconnu / None → traité comme "custom".
    - Pour "custom" : utilise les valeurs fournies telles quelles.
    - Pour les autres : preset.base_url sauf si `base_url` est fourni
      (override explicite). Idem pour le modèle.
    - `api_key` : toujours celui fourni (jamais déduit du preset). Pour les
      providers qui n'exigent pas de clé (ollama), une valeur sentinelle
      "ollama" est utilisée si vide pour satisfaire la lib.

    Retourne (effective_base_url, effective_api_key, effective_model).
    """
    p = (provider or "custom").strip().lower()
    if p not in PROVIDER_PRESETS:
        p = "custom"

    preset = PROVIDER_PRESETS[p]
    eff_base_url = (base_url or "").strip() or preset["base_url"]
    eff_model = (model or "").strip() or preset["default_model"]

    eff_key = (api_key or "").strip()
    if not eff_key:
        # Lib OpenAI-Python exige un str non-vide ; on met une sentinelle
        # pour les providers ne demandant pas de clé (ollama / serveur perso).
        eff_key = "not-needed"

    return eff_base_url, eff_key, eff_model
