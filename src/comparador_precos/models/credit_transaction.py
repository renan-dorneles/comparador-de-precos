# ============================================================
# src/comparador_precos/models/credit_transaction.py
# ============================================================
"""Modelo de transações de crédito (ledger)."""

import enum
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SAEnum

from comparador_precos.core.database import Base


class TransactionType(str, enum.Enum):
    """Tipos de transações de crédito."""

    ONBOARDING = "ONBOARDING"
    SCAN_REWARD = "SCAN_REWARD"
    SEARCH_COST = "SEARCH_COST"


class CreditTransaction(Base):
    """Ledger de transações de crédito - rastreabilidade completa."""

    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(Integer, nullable=False)  # positivo para ganho, negativo para gasto
    transaction_type = Column(
        SAEnum(
            TransactionType,
            name="transaction_type",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    reference_id = Column(String(255), nullable=True)  # ID da nota fiscal ou busca
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relacionamentos
    user = relationship("User", back_populates="credit_transactions")

    def __repr__(self) -> str:
        return (
            f"<CreditTransaction(id={self.id}, user_id={self.user_id}, "
            f"amount={self.amount}, type={self.transaction_type})>"
        )