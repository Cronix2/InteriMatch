"""
InteriMatch AI - Routes Authentification
"""

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.models import User, UserSettings  # noqa: F401  (UserSettings reserved for future use)
from app.schemas.schemas import UserCreate, UserResponse, TokenResponse, LoginRequest

# Importer le limiter partagé
from app.core.rate_limit import limiter

router = APIRouter()
_settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(_settings.rate_limit_register)
async def register(request: Request, user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Créer un nouveau compte utilisateur (rate-limited)."""
    normalized_email = user_in.email.strip().lower()
    full_name = user_in.full_name.strip()

    if not full_name:
        raise HTTPException(status_code=400, detail="Le nom complet est requis")

    result = await db.execute(select(User).where(User.email == normalized_email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Un compte avec cet email existe déjà")

    user = User(
        email=normalized_email,
        hashed_password=hash_password(user_in.password),
        full_name=full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(_settings.rate_limit_login)
async def login(request: Request, credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authentification et retour du token JWT (rate-limited)."""
    normalized_email = (credentials.email or "").strip().lower()
    password = (credentials.password or "").strip()

    if not normalized_email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email et mot de passe requis",
        )

    result = await db.execute(
        select(User)
        .options(selectinload(User.settings))
        .where(User.email == normalized_email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    # Check 2FA if enabled
    if user.settings and user.settings.totp_enabled:
        if not credentials.totp_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="2fa_required",
            )
        totp = pyotp.TOTP(user.settings.totp_secret)
        if not totp.verify(credentials.totp_code.strip(), valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Code 2FA invalide",
            )

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token)
