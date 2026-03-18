"""
InteriMatch AI - Point d'entrée FastAPI
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import engine, Base
from sqlalchemy import text
from app.api.routes import candidates, cv, matching, emails, auth, job_offers, bulk_upload, recruiter, two_factor
from app.api.routes import settings as settings_routes
from app.api.routes import dashboard

app_settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup : créer les tables si elles n'existent pas
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Migrations légères : ajouter les colonnes manquantes
            await conn.execute(
                text(
                    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS"
                    " ai_base_url VARCHAR(500) DEFAULT ''"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS"
                    " agency_address VARCHAR(500) DEFAULT ''"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS"
                    " agency_phone VARCHAR(50) DEFAULT ''"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS"
                    " agency_email VARCHAR(255) DEFAULT ''"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS"
                    " agency_siret VARCHAR(20) DEFAULT ''"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS"
                    " email_template TEXT DEFAULT ''"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE extracted_profiles ADD COLUMN IF NOT EXISTS"
                    " professional_domain VARCHAR(100)"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE candidates ADD COLUMN IF NOT EXISTS"
                    " processing_status VARCHAR(20) DEFAULT 'pending'"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE generated_emails ADD COLUMN IF NOT EXISTS"
                    " recruiter_email VARCHAR(255)"
                )
            )
        logger.info("Base de données initialisée")
    except Exception as e:
        logger.error("Impossible de se connecter à la base de données : %s", e)
        logger.warning("L'application démarre sans base de données")
    # Créer le répertoire d'upload (chemin absolu)
    upload_path = Path(app_settings.upload_dir).resolve()
    upload_path.mkdir(parents=True, exist_ok=True)
    logger.info("Répertoire d'upload : %s", upload_path)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=app_settings.app_name,
    description="Application métier pour les entreprises d'intérim — matching CV / offres d'emploi avec IA",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in app_settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.exceptions import HTTPException as FastAPIHTTPException

@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    """Garantir les headers CORS sur les HTTPException (4xx, 5xx)."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all pour garantir les headers CORS même sur les erreurs 500."""
    logger.exception("Erreur non gérée: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})


# Montage des routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentification"])
app.include_router(two_factor.router, prefix="/api/v1/auth/2fa", tags=["2FA"])
app.include_router(candidates.router, prefix="/api/v1/candidates", tags=["Candidats"])
app.include_router(cv.router, prefix="/api/v1/cv", tags=["CV"])
app.include_router(job_offers.router, prefix="/api/v1/job-offers", tags=["Offres d'emploi"])
app.include_router(matching.router, prefix="/api/v1/matching", tags=["Matching"])
app.include_router(emails.router, prefix="/api/v1/emails", tags=["Emails"])
app.include_router(settings_routes.router, prefix="/api/v1/settings", tags=["Paramètres"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(bulk_upload.router, prefix="/api/v1/bulk-upload", tags=["Upload groupé"])
app.include_router(recruiter.router, prefix="/api/v1/recruiter", tags=["Recruteur"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": app_settings.app_name}
