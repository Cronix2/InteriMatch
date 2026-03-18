"""
InteriMatch AI - Routes Authentification à deux facteurs (2FA / TOTP)
"""

import io
import base64

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, UserSettings

router = APIRouter()


@router.post("/setup")
async def setup_2fa(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Génère un secret TOTP et retourne le QR code pour configuration."""
    import uuid as _uuid

    user_id = _uuid.UUID(user["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # Get or create settings
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = settings_result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.flush()

    if settings.totp_enabled:
        raise HTTPException(status_code=400, detail="La 2FA est déjà activée")

    # Generate new secret
    secret = pyotp.random_base32()
    settings.totp_secret = secret
    await db.commit()

    # Generate provisioning URI
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=db_user.email, issuer_name="InteriMatch AI")

    # Generate QR code as base64
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    qr_b64 = base64.b64encode(buffer.read()).decode("utf-8")

    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_b64}",
        "uri": uri,
    }


@router.post("/verify")
async def verify_2fa(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Vérifie un code TOTP et active la 2FA si valide."""
    import uuid as _uuid

    code = body.get("code", "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code requis")

    user_id = _uuid.UUID(user["sub"])
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = settings_result.scalar_one_or_none()
    if not settings or not settings.totp_secret:
        raise HTTPException(status_code=400, detail="Configuration 2FA non initialisée")

    totp = pyotp.TOTP(settings.totp_secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Code invalide")

    settings.totp_enabled = True
    await db.commit()

    return {"enabled": True, "message": "2FA activée avec succès"}


@router.post("/disable")
async def disable_2fa(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Désactive la 2FA après vérification du code."""
    import uuid as _uuid

    code = body.get("code", "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code requis")

    user_id = _uuid.UUID(user["sub"])
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = settings_result.scalar_one_or_none()
    if not settings or not settings.totp_enabled:
        raise HTTPException(status_code=400, detail="La 2FA n'est pas activée")

    totp = pyotp.TOTP(settings.totp_secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Code invalide")

    settings.totp_enabled = False
    settings.totp_secret = None
    await db.commit()

    return {"enabled": False, "message": "2FA désactivée"}
