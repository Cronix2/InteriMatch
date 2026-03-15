"""
InteriMatch AI - Configuration applicative
Charge les variables d'environnement depuis .env
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- Application ---
    app_name: str = "InteriMatch AI"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # --- Base de données ---
    database_url: str = "postgresql+asyncpg://interimatch:interimatch@localhost:5432/interimatch"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- IA / LLM ---
    ai_model: str = "alfred-4.2"
    ai_server_url: str = "https://trust.liveintelligence.orange-business.com"
    ai_api_key: str = ""
    ai_temperature: float = 0.3
    ai_max_tokens: int = 2000

    # --- France Travail API ---
    france_travail_client_id: str = ""
    france_travail_client_secret: str = ""
    france_travail_base_url: str = "https://api.francetravail.io/partenaire/offresdemploi/v2"
    france_travail_auth_url: str = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"

    # --- JWT / Sécurité ---
    secret_key: str = "CHANGEZ-MOI-EN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # --- Upload ---
    max_upload_size: int = 10_485_760  # 10 Mo
    upload_dir: str = "./uploads"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
