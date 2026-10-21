# ============================================================
# src/comparador_precos/models/invoice.py
# ============================================================
"""Modelos de Nota Fiscal (NFC-e) e itens."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Float,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from comparador_precos.core.database import Base


class Invoice(Base):
    """Nota Fiscal Eletrônica (NFC-e) processada."""

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_key = Column(
        String(44),
        unique=True,
        index=True,
        nullable=False,
        comment="Chave de acesso SEFAZ (44 dígitos)",
    )
    issue_date = Column(DateTime(timezone=True), nullable=False)
    total_value = Column(Float, nullable=False)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_html = Column(Text, nullable=True)  # HTML bruto da SEFAZ-RS
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit = Column(String(20), nullable=False)  # UN, KG, etc
    price = Column(Float, nullable=False)
    catalog_product_id = Column(
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