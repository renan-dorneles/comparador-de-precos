# ============================================================
# alembic/versions/20240115_001_initial_schema.py
# ============================================================
"""Schema inicial - todos os modelos do sistema.

Revision ID: 20240115_001
Revises:
Create Date: 2024-01-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20240115_001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ensure_postgis_extension() -> None:
    """Habilita a extensão PostGIS de forma idempotente.

    A coluna ``stores.location`` usa o tipo ``geometry(POINT, 4326)``, que só
    existe se a extensão estiver habilitada no banco. Em Postgres gerenciados
    (Railway/Render) a extensão já vem instalada e o usuário da aplicação
    pode não ter permissão para criá-la - nesse caso apenas verificamos.
    """
    bind = op.get_bind()
    already_installed = bind.execute(
        sa.text("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
    ).scalar()
    if already_installed:
        return

    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    except sa.exc.OperationalError as exc:
        raise RuntimeError(
            "Não foi possível habilitar a extensão PostGIS. "
            "Verifique se a imagem do banco é 'postgis/postgis' ou habilite a "
            "extensão manualmente com superusuário. Detalhe: " + str(exc)
        ) from exc


def upgrade() -> None:
    """Criar todas as tabelas iniciais."""
    # A extensão precisa existir antes da criação de 'stores' (coluna geometry)
    _ensure_postgis_extension()

    # Tabela de tipos de transação (enum separado para reusabilidade)
    transaction_type_enum = postgresql.ENUM(
        "ONBOARDING",
        "SCAN_REWARD",
        "SEARCH_COST",
        name="transaction_type",
    )
    transaction_type_enum.create(op.get_bind())

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("credit_balance", sa.Integer, default=20, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # stores
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("cnpj", sa.String(18), unique=True, nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("location", Geometry("POINT", srid=4326), nullable=True),
        sa.Column("city", sa.String(100), nullable=True, index=True),
        sa.Column("state", sa.String(2), nullable=True, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # product_catalog
    op.create_table(
        "product_catalog",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("generic_name", sa.String(255), nullable=False, index=True),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("category", sa.String(100), nullable=True, index=True),
        sa.Column("unit_of_measure", sa.String(20), nullable=True),
    )

    # invoices
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "access_key",
            sa.String(44),
            unique=True,
            index=True,
            nullable=False,
            comment="Chave de acesso SEFAZ (44 digitos)",
        ),
        sa.Column("issue_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_value", sa.Float, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("raw_html", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # invoice_items
    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "invoice_id",
            sa.Integer,
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column(
            "catalog_product_id",
            sa.Integer,
            sa.ForeignKey("product_catalog.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # credit_transactions
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column(
            "transaction_type",
            # create_type=False: o tipo ja foi criado explicitamente acima.
            # Sem isso o create_table tentaria cria-lo novamente e falharia
            # com 'type "transaction_type" already exists'.
            postgresql.ENUM(
                "ONBOARDING",
                "SCAN_REWARD",
                "SEARCH_COST",
                name="transaction_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("reference_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # store_prices
    op.create_table(
        "store_prices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "store_id",
            sa.Integer,
            sa.ForeignKey("stores.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "catalog_product_id",
            sa.Integer,
            sa.ForeignKey("product_catalog.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "invoice_item_id",
            sa.Integer,
            sa.ForeignKey("invoice_items.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # Indice GIST para consultas geograficas via PostGIS
    op.execute("CREATE INDEX ix_stores_location_gist ON stores USING GIST (location)")


def downgrade() -> None:
    """Reverter criacao de todas as tabelas."""
    op.execute("DROP INDEX IF EXISTS ix_stores_location_gist")
    op.drop_table("store_prices")
    op.drop_table("credit_transactions")
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.drop_table("product_catalog")
    op.drop_table("stores")
    op.drop_table("users")

    postgresql.ENUM(
        "ONBOARDING",
        "SCAN_REWARD",
        "SEARCH_COST",
        name="transaction_type",
    ).drop(op.get_bind())
