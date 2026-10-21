# ============================================================
# src/comparador_precos/schemas/__init__.py
# ============================================================
"""Schemas Pydantic (serialização/validação de API)."""

from comparador_precos.schemas.user import UserCreate, UserRead, UserUpdate
from comparador_precos.schemas.credit import (
    CreditTransactionRead,
    CreditBalanceRead,
    CreditEntry,
)
from comparador_precos.schemas.invoice import (
    InvoiceCreate,
    InvoiceRead,
    InvoiceItemRead,
)
from comparador_precos.schemas.product import (
    ProductCatalogRead,
    ProductCatalogCreate,
)

__all__ = [
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "CreditTransactionRead",
    "CreditBalanceRead",
    "CreditEntry",
    "InvoiceCreate",
    "InvoiceRead",
    "InvoiceItemRead",
    "ProductCatalogRead",
    "ProductCatalogCreate",
]