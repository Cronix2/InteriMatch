"""
InteriMatch AI - Point d'entrée FastAPI
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
from app.api.routes import candidates, cv, matching, emails, auth, job_offers

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup : créer les tables si elles n'existent pas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Créer le répertoire d'upload
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="Application métier pour les entreprises d'intérim — matching CV / offres d'emploi avec IA",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montage des routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentification"])
app.include_router(candidates.router, prefix="/api/v1/candidates", tags=["Candidats"])
app.include_router(cv.router, prefix="/api/v1/cv", tags=["CV"])
app.include_router(job_offers.router, prefix="/api/v1/job-offers", tags=["Offres d'emploi"])
app.include_router(matching.router, prefix="/api/v1/matching", tags=["Matching"])
app.include_router(emails.router, prefix="/api/v1/emails", tags=["Emails"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}
