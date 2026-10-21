# ============================================================
# src/comparador_precos/core/config.py
# ============================================================
"""Configurações da aplicação via pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Comparador de Preços"
    debug: bool = False

    # Database
    database_url: str = Field(
        default="postgresql://comparador_user:comparador_pass@localhost:5432/comparador_precos",
        description="URL de conexão PostgreSQL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL de conexão Redis",
    )

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Chave secreta para JWT",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # NFC-e
    sefaz_base_url: str = "https://www.nfce.sefaz.rs.gov.br/nfce-web/consultaNFCe.jsp"
    nfce_rate_limit_per_day: int = 3
    nfce_max_age_days: int = 7

    # Credits
    onboarding_credits: int = 20
    search_cost_credits: int = 1
    scan_reward_credits: int = 5


@lru_cache()
def get_settings() -> Settings:
    """Retorna instância singleton das configurações."""
    return Settings()