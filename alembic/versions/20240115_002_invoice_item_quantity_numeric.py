# ============================================================
# alembic/versions/20240115_002_invoice_item_quantity_numeric.py
# ============================================================
"""Altera ``invoice_items.quantity`` para Numeric (quantidades fracionadas).

NFC-e reales registram quantidades fracionadas (ex.: "0,5 KG" de pão), que
eram truncadas para inteiro. A busca da Fase 4 precisa da quantidade real
para calcular o custo da cesta.

Revision ID: 20240115_002
Revises: 20240115_001
Create Date: 2024-01-16

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20240115_002"
down_revision: str | None = "20240115_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Converte a coluna de quantidade para Numeric(10, 3)."""
    op.alter_column(
        "invoice_items",
        "quantity",
        type_=sa.Numeric(10, 3),
        existing_type=sa.Integer(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Volta a coluna de quantidade para Integer (arredondando)."""
    op.alter_column(
        "invoice_items",
        "quantity",
        type_=sa.Integer(),
        existing_type=sa.Numeric(10, 3),
        existing_nullable=False,
    )
