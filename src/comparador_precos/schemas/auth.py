# ============================================================
# src/comparador_precos/schemas/auth.py
# ============================================================
"""Schemas Pydantic para autenticação."""

from datetime import datetime

from pydantic import BaseModel, Field


class Token(BaseModel):
    """Resposta de autenticação com token JWT."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Validade do token em segundos")
    credit_balance: int = Field(..., description="Saldo de créditos do usuário")


class RefreshTokenRequest(BaseModel):
    """Request para renovar o token de acesso."""

    refresh_token: str


class TokenPayload(BaseModel):
    """Payload decodificado do JWT."""

    sub: int | None = None
    exp: datetime | None = None
    type: str | None = None
