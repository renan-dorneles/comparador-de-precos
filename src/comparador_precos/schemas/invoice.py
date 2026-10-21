# ============================================================
# src/comparador_precos/schemas/invoice.py
# ============================================================
"""Schemas Pydantic para notas fiscais."""

from datetime import datetime

from pydantic import BaseModel, Field


class InvoiceItemRead(BaseModel):
    id: int
    invoice_id: int
    description: str = Field(..., max_length=500)
    quantity: int
    unit: str = Field(..., max_length=20)
    price: float = Field(..., ge=0)
    catalog_product_id: int | None = None

    class Config:
        from_attributes = True


class InvoiceRead(BaseModel):
    id: int
    access_key: str = Field(..., min_length=44, max_length=44)
    issue_date: datetime
    total_value: float = Field(..., ge=0)
    user_id: int | None = None
    raw_html: str | None = None
    created_at: datetime
    items: list[InvoiceItemRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    access_key: str = Field(..., min_length=44, max_length=44)
    issue_date: datetime
    total_value: float = Field(..., ge=0)
    items: list[InvoiceItemRead] = Field(..., min_length=1, description="Itens da nota fiscal")
