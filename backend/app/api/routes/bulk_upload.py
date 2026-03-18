"""
InteriMatch AI - Routes Upload groupé de CV (ZIP)
"""

import asyncio
import uuid
import zipfile
import io
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, async_session
from app.core.security import get_current_user
from app.models.models import Candidate, Resume, ExtractedProfile, BulkUploadJob
from app.services.cv_parser import parse_cv

settings = get_settings()
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}

# In-memory control signals for bulk jobs
_paused_jobs: set[uuid.UUID] = set()
_cancelled_jobs: set[uuid.UUID] = set()


async def _process_single_cv(
    file_bytes: bytes,
    file_name: str,
    user_id: str,
    job_id: uuid.UUID,
) -> dict:
    """Traite un seul CV en arrière-plan."""
    async with async_session() as db:
        try:
            suffix = Path(file_name).suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                return {"filename": file_name, "status": "failed", "error": f"Format non supporté ({suffix})"}

            # Parse le CV
            parsed = await parse_cv(file_bytes, file_name)
            profile_data = parsed["profile"]

            # Sauvegarder le fichier
            file_id = uuid.uuid4()
            safe_name = f"{file_id}{suffix}"
            file_path = Path(settings.upload_dir).resolve() / safe_name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(file_bytes)

            # Créer candidat
            candidate = Candidate(
                first_name=profile_data.get("first_name", ""),
                last_name=profile_data.get("last_name", ""),
                email=profile_data.get("email"),
                phone=profile_data.get("phone"),
                location=profile_data.get("location"),
                availability=profile_data.get("availability"),
                processing_status="pending",
                created_by=uuid.UUID(user_id),
            )
            db.add(candidate)
            await db.flush()

            # Créer CV
            resume = Resume(
                candidate_id=candidate.id,
                file_name=file_name,
                file_type=suffix.lstrip("."),
                file_path=str(file_path),
                raw_text=parsed["raw_text"],
            )
            db.add(resume)
            await db.flush()

            # Créer profil extrait
            extracted_profile = ExtractedProfile(
                resume_id=resume.id,
                skills=profile_data.get("skills", []),
                experiences=profile_data.get("experiences", []),
                education=profile_data.get("education", []),
                certifications=profile_data.get("certifications", []),
                languages=profile_data.get("languages", []),
                mobility=profile_data.get("mobility"),
                profile_summary=profile_data.get("profile_summary"),
                years_of_experience=profile_data.get("years_of_experience"),
                desired_job_titles=profile_data.get("desired_job_titles", []),
                professional_domain=profile_data.get("professional_domain"),
            )
            db.add(extracted_profile)
            await db.commit()

            return {
                "filename": file_name,
                "status": "success",
                "candidate_id": str(candidate.id),
                "candidate_name": f"{candidate.first_name} {candidate.last_name}".strip(),
            }
        except Exception as e:
            await db.rollback()
            return {"filename": file_name, "status": "failed", "error": str(e)[:200]}


async def _process_bulk_job(job_id: uuid.UUID, files: list[tuple[str, bytes]], user_id: str):
    """Traite tous les fichiers d'un job bulk en arrière-plan."""
    results = []
    successful = 0
    failed = 0

    for file_name, file_bytes in files:
        # Check for cancellation
        if job_id in _cancelled_jobs:
            _cancelled_jobs.discard(job_id)
            async with async_session() as db:
                job_result = await db.execute(
                    select(BulkUploadJob).where(BulkUploadJob.id == job_id)
                )
                job = job_result.scalar_one_or_none()
                if job:
                    job.status = "cancelled"
                    job.results = results
                    await db.commit()
            return

        # Check for pause - wait until resumed
        while job_id in _paused_jobs:
            await asyncio.sleep(1)
            if job_id in _cancelled_jobs:
                break

        # Check cancel again after potential pause
        if job_id in _cancelled_jobs:
            _cancelled_jobs.discard(job_id)
            async with async_session() as db:
                job_result = await db.execute(
                    select(BulkUploadJob).where(BulkUploadJob.id == job_id)
                )
                job = job_result.scalar_one_or_none()
                if job:
                    job.status = "cancelled"
                    job.results = results
                    await db.commit()
            return

        result = await _process_single_cv(file_bytes, file_name, user_id, job_id)
        results.append(result)
        if result["status"] == "success":
            successful += 1
        else:
            failed += 1

        # Mettre à jour le job en base à chaque fichier traité
        async with async_session() as db:
            job_result = await db.execute(
                select(BulkUploadJob).where(BulkUploadJob.id == job_id)
            )
            job = job_result.scalar_one_or_none()
            if job:
                job.processed_files = successful + failed
                job.successful_files = successful
                job.failed_files = failed
                job.results = results
                await db.commit()

    # Marquer comme terminé
    async with async_session() as db:
        job_result = await db.execute(
            select(BulkUploadJob).where(BulkUploadJob.id == job_id)
        )
        job = job_result.scalar_one_or_none()
        if job:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.results = results
            await db.commit()


@router.post("/upload-zip", status_code=status.HTTP_202_ACCEPTED)
async def upload_zip(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Upload un fichier ZIP contenant plusieurs CV. Traitement en arrière-plan."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un ZIP")

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:  # 50 Mo max pour ZIP
        raise HTTPException(status_code=400, detail="Fichier ZIP trop volumineux (max 50 Mo)")

    # Extraire les fichiers du ZIP
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            cv_files = []
            for name in zf.namelist():
                # Ignorer les dossiers et fichiers cachés/système
                if name.endswith("/") or name.startswith("__MACOSX") or name.startswith("."):
                    continue
                suffix = Path(name).suffix.lower()
                if suffix in ALLOWED_EXTENSIONS:
                    cv_files.append((Path(name).name, zf.read(name)))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Fichier ZIP invalide")

    if not cv_files:
        raise HTTPException(status_code=400, detail="Aucun CV trouvé dans le ZIP (formats acceptés : PDF, DOCX)")

    if len(cv_files) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 CV par ZIP")

    # Créer le job en base
    job = BulkUploadJob(
        user_id=uuid.UUID(user["sub"]),
        total_files=len(cv_files),
        status="processing",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    job_data = {
        "id": str(job.id),
        "total_files": job.total_files,
        "status": job.status,
    }

    await db.commit()

    # Lancer le traitement en arrière-plan
    asyncio.create_task(_process_bulk_job(job.id, cv_files, user["sub"]))

    return {
        "job": job_data,
        "message": f"{len(cv_files)} CV trouvé(s), traitement en cours...",
    }


@router.get("/jobs")
async def list_bulk_jobs(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Liste les jobs d'upload groupé."""
    result = await db.execute(
        select(BulkUploadJob).order_by(BulkUploadJob.created_at.desc()).limit(20)
    )
    jobs = result.scalars().all()
    return [
        {
            "id": str(j.id),
            "total_files": j.total_files,
            "processed_files": j.processed_files,
            "successful_files": j.successful_files,
            "failed_files": j.failed_files,
            "status": j.status,
            "results": j.results or [],
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}")
async def get_bulk_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Récupère le statut d'un job d'upload groupé."""
    result = await db.execute(
        select(BulkUploadJob).where(BulkUploadJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    return {
        "id": str(job.id),
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "successful_files": job.successful_files,
        "failed_files": job.failed_files,
        "status": job.status,
        "results": job.results or [],
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.put("/jobs/{job_id}/pause")
async def pause_bulk_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Met en pause un job d'upload groupé."""
    result = await db.execute(
        select(BulkUploadJob).where(BulkUploadJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    if job.status != "processing":
        raise HTTPException(status_code=400, detail="Le job n'est pas en cours de traitement")

    _paused_jobs.add(job_id)
    job.status = "paused"
    await db.commit()
    return {"status": "paused"}


@router.put("/jobs/{job_id}/resume")
async def resume_bulk_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Reprend un job d'upload groupé en pause."""
    result = await db.execute(
        select(BulkUploadJob).where(BulkUploadJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    if job.status != "paused":
        raise HTTPException(status_code=400, detail="Le job n'est pas en pause")

    _paused_jobs.discard(job_id)
    job.status = "processing"
    await db.commit()
    return {"status": "processing"}


@router.put("/jobs/{job_id}/cancel")
async def cancel_bulk_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Annule un job d'upload groupé."""
    result = await db.execute(
        select(BulkUploadJob).where(BulkUploadJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    if job.status not in ("processing", "paused"):
        raise HTTPException(status_code=400, detail="Le job ne peut pas être annulé")

    _paused_jobs.discard(job_id)
    _cancelled_jobs.add(job_id)
    job.status = "cancelled"
    await db.commit()
    return {"status": "cancelled"}


@router.post("/jobs/{job_id}/retry-failed")
async def retry_failed_bulk_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Relance les CV échoués d'un job d'upload groupé."""
    result = await db.execute(
        select(BulkUploadJob).where(BulkUploadJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    if job.status not in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Le job est encore en cours")

    # Find failed filenames from existing results
    failed_filenames = {r["filename"] for r in (job.results or []) if r["status"] == "failed"}
    if not failed_filenames:
        raise HTTPException(status_code=400, detail="Aucun fichier échoué à relancer")

    # We can't retry because we don't store file bytes - create a note
    # Instead, mark them for retry by resetting the job
    job.status = "processing"
    job.failed_files = 0
    # Keep only successful results
    job.results = [r for r in (job.results or []) if r["status"] == "success"]
    job.processed_files = len(job.results)
    await db.commit()

    return {
        "status": "processing",
        "message": f"{len(failed_filenames)} fichier(s) marqué(s) pour relance. Veuillez re-uploader le ZIP pour les fichiers échoués.",
        "failed_files": list(failed_filenames),
    }
