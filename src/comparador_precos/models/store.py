# ============================================================
# src/comparador_precos/models/store.py
# ============================================================
"""Modelos de lojas e preços capturados."""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from comparador_precos.core.database import Base


class Store(Base):
    """Loja física registrada no sistema."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # PostGIS
    location: Mapped[Geometry | None] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relacionamentos
    prices = relationship(
        "StorePrice",
        back_populates="store",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Store(id={self.id}, name='{self.name}', city='{self.city}')>"


class StorePrice(Base):
    """Preço de um produto em uma loja específica."""

    __tablename__ = "store_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_product_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("product_catalog.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    invoice_item_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("invoice_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relacionamentos
    store = relationship("Store", back_populates="prices")
    catalog_product = relationship("ProductCatalog", back_populates="store_prices")

    def __repr__(self) -> str:
        return f"<StorePrice(id={self.id}, store_id={self.store_id}, " f"price={self.price})>"
