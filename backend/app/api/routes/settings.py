"""
InteriMatch AI - Routes Paramètres utilisateur
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password, hash_password
from app.api.deps import get_current_user_db
from app.models.models import User, UserSettings
from app.schemas.schemas import (
    UserProfileResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
    PasswordChangeRequest,
)
from sqlalchemy import select

router = APIRouter()


def _settings_to_response(s: UserSettings | None) -> UserSettingsResponse:
    if not s:
        return UserSettingsResponse()
    return UserSettingsResponse(
        first_name=s.first_name or "",
        last_name=s.last_name or "",
        company_name=s.company_name or "",
        theme=s.theme or "system",
        agency_address=s.agency_address or "",
        agency_phone=s.agency_phone or "",
        agency_email=s.agency_email or "",
        agency_siret=s.agency_siret or "",
        email_template=s.email_template or "",
        ai_provider=s.ai_provider or "",
        ai_model=s.ai_model or "",
        ai_base_url=s.ai_base_url or "",
        ai_temperature=s.ai_temperature,
        ai_api_key_set=bool(s.ai_api_key),
        france_travail_client_id=s.france_travail_client_id or "",
        france_travail_secret_set=bool(s.france_travail_client_secret),
        hunter_api_key_set=bool(s.hunter_api_key),
        smtp_host=s.smtp_host or "",
        smtp_port=s.smtp_port,
        smtp_user=s.smtp_user or "",
        smtp_password_set=bool(s.smtp_password),
        smtp_use_tls=bool(s.smtp_use_tls) if s.smtp_use_tls is not None else True,
        smtp_from=s.smtp_from or "",
        setup_completed=_is_setup_complete(s),
        totp_enabled=s.totp_enabled or False,
    )


def _is_setup_complete(s: UserSettings | None) -> bool:
    """Vérifie que la configuration minimale est remplie."""
    if not s:
        return False
    return bool(
        s.first_name
        and s.last_name
        and s.company_name
        and s.france_travail_client_id
        and s.france_travail_client_secret
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    user: User = Depends(get_current_user_db),
):
    """Retourne le profil et les paramètres de l'utilisateur connecté."""
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        settings=_settings_to_response(user.settings),
    )


@router.put("/me", response_model=UserProfileResponse)
async def update_settings(
    data: UserSettingsUpdate,
    user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Met à jour les paramètres de l'utilisateur."""
    if not user.settings:
        user.settings = UserSettings(user_id=user.id)
        db.add(user.settings)

    s = user.settings
    # Email update (on User model directly)
    if data.email is not None:
        new_email = data.email.strip().lower()
        if new_email and new_email != user.email:
            existing = await db.execute(select(User).where(User.email == new_email))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")
            user.email = new_email
    if data.first_name is not None:
        s.first_name = data.first_name.strip()
    if data.last_name is not None:
        s.last_name = data.last_name.strip()
    if data.company_name is not None:
        s.company_name = data.company_name.strip()
    if data.theme is not None:
        if data.theme not in ("light", "dark", "system"):
            raise HTTPException(status_code=400, detail="Thème invalide")
        s.theme = data.theme
    if data.ai_api_key is not None:
        s.ai_api_key = data.ai_api_key.strip()
    if data.ai_provider is not None:
        from app.services.ai_providers import ALLOWED_PROVIDERS
        provider = data.ai_provider.strip().lower()
        if provider and provider not in ALLOWED_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"Provider IA invalide. Valeurs acceptees : {', '.join(sorted(ALLOWED_PROVIDERS))}",
            )
        s.ai_provider = provider
    if data.ai_model is not None:
        s.ai_model = data.ai_model.strip()
    if data.ai_base_url is not None:
        s.ai_base_url = data.ai_base_url.strip()
    if data.ai_temperature is not None:
        s.ai_temperature = data.ai_temperature
    if data.france_travail_client_id is not None:
        s.france_travail_client_id = data.france_travail_client_id.strip()
    if data.france_travail_client_secret is not None:
        s.france_travail_client_secret = data.france_travail_client_secret.strip()
    if data.hunter_api_key is not None:
        s.hunter_api_key = data.hunter_api_key.strip()
    if data.smtp_host is not None:
        s.smtp_host = data.smtp_host.strip()
    if data.smtp_port is not None:
        if data.smtp_port < 0 or data.smtp_port > 65535:
            raise HTTPException(status_code=400, detail="Port SMTP invalide")
        s.smtp_port = data.smtp_port
    if data.smtp_user is not None:
        s.smtp_user = data.smtp_user.strip()
    if data.smtp_password is not None:
        s.smtp_password = data.smtp_password
    if data.smtp_use_tls is not None:
        s.smtp_use_tls = bool(data.smtp_use_tls)
    if data.smtp_from is not None:
        s.smtp_from = data.smtp_from.strip()
    if data.agency_address is not None:
        s.agency_address = data.agency_address.strip()
    if data.agency_phone is not None:
        s.agency_phone = data.agency_phone.strip()
    if data.agency_email is not None:
        s.agency_email = data.agency_email.strip()
    if data.agency_siret is not None:
        s.agency_siret = data.agency_siret.strip()
    if data.email_template is not None:
        s.email_template = data.email_template

    # Mettre à jour full_name si prénom/nom modifiés
    if data.first_name is not None or data.last_name is not None:
        fn = s.first_name or ""
        ln = s.last_name or ""
        combined = f"{fn} {ln}".strip()
        if combined:
            user.full_name = combined

    await db.flush()
    await db.refresh(user)

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        settings=_settings_to_response(user.settings),
    )


@router.put("/me/password")
async def change_password(
    data: PasswordChangeRequest,
    user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Changer le mot de passe."""
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")

    user.hashed_password = hash_password(data.new_password)
    await db.flush()
    return {"detail": "Mot de passe mis à jour"}


@router.get("/ai-providers")
async def list_ai_providers(_user: User = Depends(get_current_user_db)):
    """Retourne la liste des providers IA disponibles avec leur preset par défaut."""
    from app.services.ai_providers import PROVIDER_PRESETS
    return [
        {
            "id": pid,
            "label": preset["label"],
            "base_url": preset["base_url"],
            "default_model": preset["default_model"],
            "requires_key": preset["requires_key"],
            "docs": preset["docs"],
        }
        for pid, preset in PROVIDER_PRESETS.items()
    ]
