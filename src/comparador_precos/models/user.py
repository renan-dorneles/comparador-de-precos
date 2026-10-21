# ============================================================
# src/comparador_precos/models/user.py
# ============================================================
"""Modelo de Usuário."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    func,
)
from sqlalchemy.orm import relationship

from comparador_precos.core.database import Base


class User(Base):
    """Tabla de usuários do sistema."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    credit_balance = Column(Integer, default=20, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relacionamentos
    credit_transactions = relationship(
        "CreditTransaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    invoices = relationship(
        "Invoice",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', credit_balance={self.credit_balance})>"