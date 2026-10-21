# ============================================================
# src/comparador_precos/schemas/invoice.py
# ============================================================
"""Schemas Pydantic para notas fiscais."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class InvoiceItemRead(BaseModel):
    id: int
    invoice_id: int
    description: str = Field(..., max_length=500)
    quantity: int
    unit: str = Field(..., max_length=20)
    price: float = Field(..., ge=0)
    catalog_product_id: Optional[int] = None

    class Config:
        from_attributes = True


class InvoiceRead(BaseModel):
    id: int
    access_key: str = Field(..., min_length=44, max_length=44)
    issue_date: datetime
    total_value: float = Field(..., ge=0)
    user_id: Optional[int] = None
    raw_html: Optional[str] = None
    created_at: datetime
    items: List[InvoiceItemRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    access_key: str = Field(..., min_length=44, max_length=44)
    issue_date: datetime
    total_value: float = Field(..., ge=0)
    items: List[InvoiceItemRead] = Field(
        ..., min_items=1, description="Itens da nota fiscal"
    )