# ============================================================
# src/comparador_precos/models/credit_transaction.py
# ============================================================
"""Modelo de transações de crédito (ledger)."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from comparador_precos.core.database import Base


class TransactionType(StrEnum):
    """Tipos de transações de crédito."""

    ONBOARDING = "ONBOARDING"
    SCAN_REWARD = "SCAN_REWARD"
    SEARCH_COST = "SEARCH_COST"


class CreditTransaction(Base):
    """Ledger de transações de crédito - rastreabilidade completa."""

    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # positivo para ganho, negativo para gasto
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(
            TransactionType,
            name="transaction_type",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    # ID da nota fiscal ou busca
    reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relacionamentos
    user = relationship("User", back_populates="credit_transactions")

    def __repr__(self) -> str:
        return (
            f"<CreditTransaction(id={self.id}, user_id={self.user_id}, "
            f"amount={self.amount}, type={self.transaction_type})>"
        )
