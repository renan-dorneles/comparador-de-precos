# ============================================================
# src/comparador_precos/schemas/product.py
# ============================================================
"""Schemas Pydantic para catálogo de produtos."""

from typing import Optional

from pydantic import BaseModel, Field


class ProductCatalogRead(BaseModel):
    id: int
    generic_name: str = Field(..., max_length=255)
    brand: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    unit_of_measure: Optional[str] = Field(default=None, max_length=20)

    class Config:
        from_attributes = True


class ProductCatalogCreate(BaseModel):
    generic_name: str = Field(..., max_length=255)
    brand: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    unit_of_measure: Optional[str] = Field(default=None, max_length=20)