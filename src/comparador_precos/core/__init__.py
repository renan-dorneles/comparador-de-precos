# ============================================================
# src/comparador_precos/core/__init__.py
# ============================================================
"""Core module exports.

Nota: `dependencies` NÃO é importado aqui de propósito - ele depende de
`comparador_precos.models`, que por sua vez importa `core.database`.
Importar eagerly causaria circular import.
"""

from comparador_precos.core.config import Settings, get_settings
from comparador_precos.core.database import Base, close_db, engine, get_session, init_db
from comparador_precos.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)

__all__ = [
    "Base",
    "Settings",
    "close_db",
    "create_access_token",
    "decode_access_token",
    "engine",
    "get_password_hash",
    "get_session",
    "get_settings",
    "init_db",
    "verify_password",
]
