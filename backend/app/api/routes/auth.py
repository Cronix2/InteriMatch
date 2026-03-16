"""
InteriMatch AI - Routes Authentification
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.models import User
from app.schemas.schemas import UserCreate, UserResponse, TokenResponse, LoginRequest

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Créer un nouveau compte utilisateur."""
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
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authentification et retour du token JWT."""
    normalized_email = (credentials.email or "").strip().lower()
    password = (credentials.password or "").strip()

    if not normalized_email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email et mot de passe requis",
        )

    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token)
