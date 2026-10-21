# ============================================================
# src/comparador_precos/schemas/credit.py
# ============================================================
"""Schemas Pydantic para sistema de créditos."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreditTransactionRead(BaseModel):
    id: int
    user_id: int
    amount: int = Field(
        ..., description="Quantidade de créditos (positivo para ganho, negativo para gasto)"
    )
    transaction_type: str = Field(..., description="Tipo: ONBOARDING, SCAN_REWARD, SEARCH_COST")
    reference_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CreditBalanceRead(BaseModel):
    balance: int = Field(..., description="Saldo atual de créditos")
    recent_transactions: list[CreditTransactionRead] = Field(
        default_factory=list, description="Últimas transações"
    )


class CreditEntry(BaseModel):
    """Entrada para registrar uma transação de crédito no ledger."""

    user_id: int
    amount: int
    transaction_type: str
    reference_id: str | None = None
