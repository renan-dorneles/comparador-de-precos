# ============================================================
# src/comparador_precos/services/ledger.py
# ============================================================
"""Serviço de Ledger - gerenciamento atômico de transações de crédito.

Regras (docs/ARCHITECTURE.md):
  * `users.credit_balance` guarda o saldo corrente (default 20).
  * `credit_transactions` guarda o histórico completo (audit trail).
  * Toda movimentação (débito/crédito) atualiza o saldo E registra a
    transação dentro de uma ÚNICA transação de banco de dados (ACID).

O saldo nunca é alterado sem o registro correspondente no ledger, e
vice-versa. Para evitar condições de corrida (race conditions), o usuário é
bloqueado com `SELECT ... FOR UPDATE` antes da atualização.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comparador_precos.models.user import User
from comparador_precos.models.credit_transaction import (
    CreditTransaction,
    TransactionType,
)


class InsufficientCreditsError(Exception):
    """Levantada quando o usuário não tem créditos suficientes."""


class LedgerService:
    """Gerencia todas as operações de crédito de forma atômica."""

    ONBOARDING_CREDITS: int = 20
    SCAN_REWARD_CREDITS: int = 5
    SEARCH_COST_CREDITS: int = 1

    async def get_user_for_update(self, db: AsyncSession, user_id: int) -> User:
        """Busca o usuário com lock pessimista de linha (SELECT FOR UPDATE).

        Garante que nenhum outra transação altere o saldo concorrentemente.
        """
        result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"Usuário {user_id} não encontrado")
        return user

    async def get_balance(self, db: AsyncSession, user_id: int) -> int:
        """Retorna o saldo atual de créditos do usuário."""
        result = await db.execute(
            select(User.credit_balance).where(User.id == user_id)
        )
        balance = result.scalar_one_or_none()
        return int(balance) if balance is not None else 0

    async def can_afford_search(self, db: AsyncSession, user_id: int) -> bool:
        """Verifica se o usuário tem créditos suficientes para uma busca."""
        return await self.get_balance(db, user_id) >= self.SEARCH_COST_CREDITS

    async def apply(
        self,
        db: AsyncSession,
        user_id: int,
        amount: int,
        transaction_type: TransactionType,
        reference_id: Optional[str] = None,
    ) -> CreditTransaction:
        """Aplica uma movimentação de crédito de forma atômica.

        Atualiza `users.credit_balance` e insere a linha em
        `credit_transactions` dentro da mesma transação. O commit é
        responsabilidade do chamador (para permitir composição com
        outras operações, ex.: salvar nota + conceder recompensa).

        Args:
            db: Sessão assíncrona (transação aberta)
            user_id: Usuário alvo
            amount: Quantidade (positivo = crédito, negativo = débito)
            transaction_type: Tipo da transação
            reference_id: Referência opcional (invoice_id, search_id...)

        Raises:
            InsufficientCreditsError: Se o saldo for insuficiente para débitos.
        """
        if amount == 0:
            raise ValueError("Amount não pode ser zero")

        user = await self.get_user_for_update(db, user_id)

        if amount < 0 and user.credit_balance + amount < 0:
            raise InsufficientCreditsError(
                f"Saldo insuficiente: {user.credit_balance} créditos disponíveis"
            )

        user.credit_balance += amount

        transaction = CreditTransaction(
            id=0,  # ID gerado pelo autoincrement do banco
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            reference_id=reference_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(transaction)
        await db.flush()
        return transaction

    async def process_onboarding(
        self, db: AsyncSession, user_id: int
    ) -> CreditTransaction:
        """Concede os 20 créditos iniciais de onboarding."""
        return await self.apply(
            db=db,
            user_id=user_id,
            amount=self.ONBOARDING_CREDITS,
            transaction_type=TransactionType.ONBOARDING,
        )

    async def process_scan_reward(
        self,
        db: AsyncSession,
        user_id: int,
        reference_id: Optional[str] = None,
    ) -> CreditTransaction:
        """Concede +5 créditos por NFC-e processada com sucesso."""
        return await self.apply(
            db=db,
            user_id=user_id,
            amount=self.SCAN_REWARD_CREDITS,
            transaction_type=TransactionType.SCAN_REWARD,
            reference_id=reference_id,
        )

    async def process_search_cost(
        self,
        db: AsyncSession,
        user_id: int,
        reference_id: Optional[str] = None,
    ) -> CreditTransaction:
        """Debita -1 crédito pela otimização de cesta de compras."""
        return await self.apply(
            db=db,
            user_id=user_id,
            amount=-self.SEARCH_COST_CREDITS,
            transaction_type=TransactionType.SEARCH_COST,
            reference_id=reference_id,
        )

    async def get_transaction_history(
        self, db: AsyncSession, user_id: int, limit: int = 20
    ) -> list[CreditTransaction]:
        """Retorna as transações mais recentes do usuário (mais recentes primeiro)."""
        result = await db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())