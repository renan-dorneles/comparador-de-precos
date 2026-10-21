# ============================================================
# tests/conftest.py - Fixtures para testes
# ============================================================
"""Configurações base comuns para os testes."""

import sys
from pathlib import Path

# Garante que o pacote comparador_precos possa ser importado dos testes
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
