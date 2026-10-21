# ============================================================
# src/comparador_precos/api/routes/auth.py
# ============================================================
"""Rotas de autenticação: registro, login e refresh."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comparador_precos.core.config import get_settings
from comparador_precos.core.database import get_session
from comparador_precos.core.dependencies import get_current_user
from comparador_precos.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from comparador_precos.models.user import User
from comparador_precos.schemas.auth import Token
from comparador_precos.schemas.user import UserCreate, UserRead
from comparador_precos.services.ledger import LedgerService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
ledger = LedgerService()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registra novo usuário e concede 20 créditos de onboarding",
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_session),
):
    """Cria um novo usuário.

    Concede automaticamente 20 créditos de onboarding registrados no ledger
    (transação ONBOARDING), na mesma transação de banco do cadastro.
    """
    # Verifica e-mail duplicado
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        )

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        credit_balance=0,  # será preenchido pelo ledger
        is_active=True,
    )
    db.add(user)
    await db.flush()  # gera o user.id

    # Onboarding: 20 créditos + registro no ledger (mesma transação)
    await ledger.process_onboarding(db, user.id)
    await db.commit()
    await db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Autentica usuário e retorna token JWT",
)
async def login(
    payload: UserCreate,
    db: AsyncSession = Depends(get_session),
):
    """Autentica o usuário e retorna um token JWT de acesso."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        credit_balance=user.credit_balance,
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Renova o token de acesso",
)
async def refresh_token(
    current_user: User = Depends(get_current_user),
):
    """Gera um novo token de acesso para o usuário autenticado."""
    access_token = create_access_token(
        data={"sub": str(current_user.id), "email": current_user.email},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        credit_balance=current_user.credit_balance,
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Retorna os dados do usuário autenticado",
)
async def read_me(current_user: User = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado."""
    return current_user
