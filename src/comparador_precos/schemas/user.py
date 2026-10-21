# ============================================================
# src/comparador_precos/schemas/user.py
# ============================================================
"""Schemas Pydantic para usuários."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="E-mail do usuário")


class UserCreate(UserBase):
    password: str = Field(
        ..., min_length=8, max_length=128, description="Senha (mínimo 8 caracteres)"
    )


class UserRead(UserBase):
    id: int
    credit_balance: int = Field(default=20, description="Saldo atual de créditos")
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True