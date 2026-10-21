# ============================================================
# src/comparador_precos/schemas/__init__.py
# ============================================================
"""Schemas Pydantic (serialização/validação de API)."""

from comparador_precos.schemas.credit import (
    CreditBalanceRead,
    CreditEntry,
    CreditTransactionRead,
)
from comparador_precos.schemas.invoice import (
    InvoiceCreate,
    InvoiceItemRead,
    InvoiceRead,
)
from comparador_precos.schemas.product import (
    ProductCatalogCreate,
    ProductCatalogRead,
)
from comparador_precos.schemas.user import UserCreate, UserRead, UserUpdate

__all__ = [
    "CreditBalanceRead",
    "CreditEntry",
    "CreditTransactionRead",
    "InvoiceCreate",
    "InvoiceItemRead",
    "InvoiceRead",
    "ProductCatalogCreate",
    "ProductCatalogRead",
    "UserCreate",
    "UserRead",
    "UserUpdate",
]
