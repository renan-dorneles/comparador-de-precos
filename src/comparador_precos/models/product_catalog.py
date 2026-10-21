# ============================================================
# src/comparador_precos/models/product_catalog.py
# ============================================================
"""Modelo de catálogo de produtos genéricos."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from comparador_precos.core.database import Base


class ProductCatalog(Base):
    """Catálogo de produtos genéricos (mapeamento IA)."""

    __tablename__ = "product_catalog"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generic_name = Column(String(255), nullable=False, index=True)
    brand = Column(String(255), nullable=True)  # Pode ser nulo (genérico)
    category = Column(String(100), nullable=True, index=True)
    unit_of_measure = Column(String(20), nullable=True)

    # Relacionamentos
    items = relationship("InvoiceItem", back_populates="catalog_product")
    store_prices = relationship("StorePrice", back_populates="catalog_product")

    def __repr__(self) -> str:
        return (
            f"<ProductCatalog(id={self.id}, generic_name='{self.generic_name}', "
            f"brand='{self.brand}', category='{self.category}')>"
        )