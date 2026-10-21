# ============================================================
# src/comparador_precos/models/invoice.py
# ============================================================
"""Modelos de Nota Fiscal (NFC-e) e itens."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from comparador_precos.core.database import Base


class Invoice(Base):
    """Nota Fiscal Eletrônica (NFC-e) processada."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    access_key: Mapped[str] = mapped_column(
        String(44),
        unique=True,
        index=True,
        nullable=False,
        comment="Chave de acesso SEFAZ (44 dígitos)",
    )
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # HTML bruto da SEFAZ-RS
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relacionamentos
    user = relationship("User", back_populates="invoices")
    items = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice(id={self.id}, access_key='{self.access_key}', "
            f"total_value={self.total_value})>"
        )


class InvoiceItem(Base):
    """Item de uma nota fiscal (linha do XML)."""

    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # UN, KG, etc
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    catalog_product_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("product_catalog.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relacionamentos
    invoice = relationship("Invoice", back_populates="items")
    catalog_product = relationship("ProductCatalog", back_populates="items")

    def __repr__(self) -> str:
        return (
            f"<InvoiceItem(id={self.id}, invoice_id={self.invoice_id}, "
            f"description='{self.description}', price={self.price})>"
        )
