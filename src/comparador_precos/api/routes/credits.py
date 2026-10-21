# ============================================================
# src/comparador_precos/api/routes/credits.py
# ============================================================
"""Rotas de consulta de créditos do usuário."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from comparador_precos.core.database import get_session
from comparador_precos.core.dependencies import get_current_user
from comparador_precos.models.user import User
from comparador_precos.schemas.credit import (
    CreditBalanceRead,
    CreditTransactionRead,
)
from comparador_precos.services.ledger import LedgerService

router = APIRouter(prefix="/me", tags=["credits"])
ledger = LedgerService()


@router.get(
    "/credits",
    response_model=CreditBalanceRead,
    summary="Retorna saldo de créditos e transações recentes",
)
async def get_my_credits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Retorna o saldo atual de créditos e as últimas transações do ledger."""
    balance = await ledger.get_balance(db, current_user.id)
    raw_transactions = await ledger.get_transaction_history(db, current_user.id, limit=20)
    recent_transactions = [CreditTransactionRead.model_validate(t) for t in raw_transactions]

    return CreditBalanceRead(
        balance=balance,
        recent_transactions=recent_transactions,
    )
