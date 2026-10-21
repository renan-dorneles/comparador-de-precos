# ============================================================
# src/comparador_precos/core/rate_limit.py
# ============================================================
"""Rate limiting com Redis (regra: 3 scans NFC-e por usuário/dia)."""

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status

from comparador_precos.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class RateLimiter:
    """Rate limiter baseado em Redis com janela diária (rolling 24h)."""

    def __init__(self, redis_client=None):
        self._redis = redis_client

    async def get_redis(self):
        """Obtém (ou cria) o cliente Redis sob demanda."""
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    @staticmethod
    def _key(user_id: int, action: str) -> str:
        """Chave Redis: rate_limit:{action}:{user_id}:{YYYY-MM-DD}."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return f"rate_limit:{action}:{user_id}:{today}"

    async def check_and_increment(self, user_id: int, action: str, limit: int) -> None:
        """Verifica o limite e incrementa o contador. Levanta HTTP 429 se exceder.

        Args:
            user_id: Usuário alvo
            action: Nome da ação (ex.: "nfce_scan")
            limit: Máximo de requisições permitidas na janela
        """
        redis = await self.get_redis()
        key = self._key(user_id, action)

        try:
            current = await redis.incr(key)
            if current == 1:
                # Expira no fim do dia UTC da janela
                await redis.expireat(
                    key,
                    int(
                        datetime.now(UTC)
                        .replace(hour=23, minute=59, second=59, microsecond=0)
                        .timestamp()
                    ),
                )
        except Exception as exc:
            # Falha no Redis não deve bloquear o usuário (fail-open)
            logger.warning("Rate limiter indisponível, liberando requisição: %s", exc)
            return

        if current > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Limite de {limit} requisições por dia excedido. " "Tente novamente amanhã."
                ),
            )

    async def get_usage(self, user_id: int, action: str) -> int:
        """Retorna quantas vezes a ação foi usada na janela atual."""
        redis = await self.get_redis()
        try:
            value = await redis.get(self._key(user_id, action))
            return int(value) if value else 0
        except Exception as exc:
            logger.warning("Falha ao consultar contador de rate limit: %s", exc)
            return 0

    async def reset(self, user_id: int, action: str) -> None:
        """Zera o contador (uso em testes)."""
        redis = await self.get_redis()
        try:
            await redis.delete(self._key(user_id, action))
        except Exception as exc:
            logger.warning("Falha ao resetar contador de rate limit: %s", exc)

    async def close(self) -> None:
        """Fecha a conexão Redis."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


# Instância global
rate_limiter = RateLimiter()
