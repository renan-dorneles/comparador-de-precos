# ============================================================
# src/comparador_precos/models/store.py
# ============================================================
"""Modelos de lojas e preços capturados."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from comparador_precos.core.database import Base


class Store(Base):
    """Loja física registrada no sistema."""

    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    cnpj = Column(String(18), unique=True, nullable=True)
    address = Column(Text, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)  # PostGIS
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(2), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(
        Integer,
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_product_id = Column(
        Integer,
        ForeignKey("product_catalog.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    price = Column(Float, nullable=False)
    captured_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    invoice_item_id = Column(
        Integer,
        ForeignKey("invoice_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relacionamentos
    store = relationship("Store", back_populates="prices")
    catalog_product = relationship("ProductCatalog", back_populates="store_prices")

    def __repr__(self) -> str:
        return (
            f"<StorePrice(id={self.id}, store_id={self.store_id}, "
            f"price={self.price})>"
        )