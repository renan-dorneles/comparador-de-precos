# ============================================================
# src/comparador_precos/core/__init__.py
# ============================================================
"""Core module exports.

Nota: `dependencies` NÃO é importado aqui de propósito - ele depende de
`comparador_precos.models`, que por sua vez importa `core.database`.
Importar eagerly causaria circular import.
"""

from comparador_precos.core.config import Settings, get_settings
from comparador_precos.core.database import Base, engine, get_session, init_db, close_db
from comparador_precos.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)

__all__ = [
    "Settings",
    "get_settings",
    "Base",
    "engine",
    "get_session",
    "init_db",
    "close_db",
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
]