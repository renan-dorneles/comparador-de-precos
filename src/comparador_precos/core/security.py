# ============================================================
# src/comparador_precos/core/security.py
# ============================================================
"""Utilitários de segurança: hash de senha e JWT.

Nota: usa a biblioteca `bcrypt` diretamente (e não `passlib`) porque o
passlib 1.7.4 é incompatível com bcrypt >= 4.1 (o atributo
`bcrypt.__about__.__version__` foi removido e o limite de 72 bytes passou
a levantar `ValueError`). O bcrypt puro é a API oficial e está mantido.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt
from pydantic import ValidationError

from comparador_precos.core.config import get_settings

settings = get_settings()

# Limite do bcrypt para o tamanho da senha em bytes
BCRYPT_MAX_BYTES = 72


def _prepare_password(password: str) -> bytes:
    """Codifica a senha para bytes, truncando no limite do bcrypt."""
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        encoded = encoded[:BCRYPT_MAX_BYTES]
    return encoded


def get_password_hash(password: str) -> str:
    """Gera hash bcrypt da senha (salt aleatório embutido)."""
    hashed = bcrypt.hashpw(_prepare_password(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    try:
        return bcrypt.checkpw(
            _prepare_password(plain_password),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # Hash malformado
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Cria token JWT de acesso."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decodifica e valida token JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload
    except (jwt.JWTError, ValidationError):
        return None