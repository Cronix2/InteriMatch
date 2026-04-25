"""
InteriMatch AI - Configuration applicative
Charge les variables d'environnement depuis .env et valide les secrets critiques.
"""

import logging
import secrets
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


# Secrets reconnus comme placeholders et donc rejetés en production
_INSECURE_SECRET_PREFIXES = (
    "CHANGEZ-MOI",
    "changeme",
    "change-me",
    "your-secret",
    "test-secret",
)


class Settings(BaseSettings):
    # --- Application ---
    app_name: str = "InteriMatch AI"
    app_env: str = "development"  # development | staging | production
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # --- Base de données ---
    database_url: str = ""

    # --- Redis ---
    redis_url: str = ""

    # --- IA / LLM ---
    ai_provider: str = "custom"  # groq | openrouter | mistral | together | ollama | custom
    ai_model: str = "alfred-4.2"
    ai_server_url: str = "https://trust.liveintelligence.orange-business.com/api/v2"
    ai_api_key: str = ""
    ai_temperature: float = 0.3
    ai_max_tokens: int = 2000

    # --- France Travail API ---
    france_travail_client_id: str = ""
    france_travail_client_secret: str = ""
    france_travail_base_url: str = "https://api.francetravail.io/partenaire/offresdemploi/v2"
    france_travail_auth_url: str = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"

    # --- Hunter.io (fallback global) ---
    hunter_api_key: str = ""

    # --- SMTP (fallback global) ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from: str = ""

    # --- JWT / Sécurité ---
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # --- Rate limiting ---
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "10/hour"
    rate_limit_default: str = "120/minute"

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Upload ---
    max_upload_size: int = 10_485_760  # 10 Mo
    upload_dir: str = "./uploads"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("app_env")
    @classmethod
    def _normalize_env(cls, v: str) -> str:
        return (v or "development").strip().lower()

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        is_prod = self.app_env in ("production", "prod", "staging")
        secret = (self.secret_key or "").strip()

        secret_is_placeholder = any(
            secret.lower().startswith(p.lower()) for p in _INSECURE_SECRET_PREFIXES
        )

        if not secret or len(secret) < 32 or secret_is_placeholder:
            if is_prod:
                raise RuntimeError(
                    "SECRET_KEY manquante, trop courte (<32 chars) ou placeholder. "
                    "Générez-en une avec: openssl rand -hex 32"
                )
            # Dev/test : générer une clé éphémère et avertir.
            ephemeral = secrets.token_hex(32)
            logger.warning(
                "⚠️  SECRET_KEY invalide ou placeholder en environnement '%s'. "
                "Une clé éphémère a été générée — tous les tokens seront invalidés "
                "au prochain redémarrage. Définissez SECRET_KEY dans .env "
                "(openssl rand -hex 32) pour une expérience stable.",
                self.app_env,
            )
            object.__setattr__(self, "secret_key", ephemeral)

        if is_prod and self.app_debug:
            logger.warning(
                "⚠️  APP_DEBUG=true en '%s' : désactivez pour éviter "
                "la fuite de SQL et de stack traces.",
                self.app_env,
            )

        if is_prod and ("*" in self.cors_origins or "localhost" in self.cors_origins):
            logger.warning(
                "⚠️  CORS_ORIGINS contient '*' ou 'localhost' en production. "
                "Restreignez aux domaines réels."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
