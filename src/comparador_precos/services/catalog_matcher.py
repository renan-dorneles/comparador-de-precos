# ============================================================
# src/comparador_precos/services/catalog_matcher.py
# ============================================================
"""Mapeamento das descrições da NFC-e para o catálogo de produtos genéricos.

A Fase 3.5 do PLAN prevê mapear as descrições comerciais da nota ("LEITE
INTEGRAL 1L") para produtos genéricos do catálogo ("LEITE INTEGRAL"), para
que o mesmo item seja comparado entre lojas.

Este módulo implementa o mapeamento **baseado em regras** (determinístico,
sem custo de API). Ele é o fallback do mapeamento por LLM: a interface
`CatalogMatcher` permite trocar a implementação por uma que use o Open Router
sem alterar o fluxo de ingestão.
"""

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comparador_precos.models.product_catalog import ProductCatalog

# Medidas sizeadas no nome do produto: "1L", "500G", "1,5L", "2KG"...
_MEASURE_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(ML|LT|L|KG|G|GR|CX|PC|UN|PCT)\b",
    re.IGNORECASE,
)

# Palavras-chave por categoria de mercearia
_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "laticínios": (
        "LEITE",
        "QUEIJO",
        "MUSSARELA",
        "IOGURTE",
        "MANTEIGA",
        "CREME DE LEITE",
        "REQUEIJAO",
        "NATA",
    ),
    "padaria": ("PAO", "BOLO", "CROISSANT", "BISCUITO", "TORTA", "PÃO", "BISNAGUITO"),
    "bebidas": (
        "REFRIGERANTE",
        "GUARANA",
        "COCA",
        "PEPSI",
        "AGUA",
        "CERVEJA",
        "SUCO",
        "REFRESCO",
        "VITAMINAS",
    ),
    "limpeza": (
        "DETERGENTE",
        "SABAO",
        "AMACIANTE",
        "ALCOOL",
        "LIMPA",
        "VEJA",
        "DESINFETANTE",
        "PAPEL HIGIENICO",
    ),
    "higiene": (
        "SHAMPOO",
        "CONDICIONADOR",
        "PASTA DE DENTE",
        "SABONETE",
        "DESODORANTE",
        "FIO DENTAL",
        "ANTISSEPTICO",
    ),
    "acougue": (
        "CARNE",
        "FRANGO",
        "LINGUICA",
        "HAMBURGUER",
        "PEITO",
        "COXINHA",
        "PECA",
        "CHARQUE",
    ),
    "hortifruti": (
        "BANANA",
        "MACACA",
        "LARANJA",
        "TOMATE",
        "ALFACE",
        "BATATA",
        "CEBOLA",
        "UVA",
        "MAMÃO",
    ),
    "mercearia": (
        "ARROZ",
        "FEIJAO",
        "MACARRON",
        "ACUCAR",
        "OLEO",
        "SAL",
        "FARINHA",
        "ATUM",
        "MILHO",
    ),
    "congelados": ("CONGELADO", "PIZZA", "NUGGET", "SORVETE", "LASANHA"),
    "petiscos": ("CHOCOLATE", "SALGADINHO", "PIPOCA", "AMENDOIM", "BISCOITO"),
    "massas": ("MACARRON", "ESPAGUETE", "NHOQUE", "LASANHA"),
    "descartaveis": (
        "GUARDA-CHUVA",
        "PAPEL ALUMINIO",
        "PLASTICO",
        "COPO",
        "SACO",
        "FILME",
        "TOALHA",
    ),
}


def _strip_accents(text: str) -> str:
    """Remove acentos ('PÃO' -> 'PAO')."""
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _tokenize(text: str) -> list[str]:
    """Divide o texto em tokens alfanuméricos em caixa alta."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", _strip_accents(text).upper())
    return [token for token in cleaned.split() if token]


def normalize_description(description: str, unit: str = "UN") -> str:
    """Normaliza a descrição de um item da NFC-e para o catálogo genérico.

    Remove acentos, coloca em caixa alta, elimina medidas numéricas e
    o sufixo da unidade de medida quando esta aparece no final.

    Args:
        description: Texto bruto da descrição do item (ex: "LEITE INTEGRAL 1L").
        unit: Unidade de medida do item (ex: "UN", "KG"). Usada para remover
            o sufixo final quando coincidir.

    Returns:
        Descrição normalizada em caixa alta sem acentos, sem medidas numéricas
        e sem a unidade no final. Texto vazio retorna vazio.
    """
    if not description or not description.strip():
        return ""

    cleaned = _strip_accents(description).upper()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Remove medidas numéricas seguidas de unidade de medida (ex: "1L", "1,5KG", "500G")
    cleaned = _MEASURE_PATTERN.sub("", cleaned)

    # Remove a unidade informada quando aparecer como token isolado no final
    if unit:
        unit_upper = _strip_accents(unit).upper().strip()
        # Remove a unidade se aparecer como última palavra (com espaço antes)
        cleaned = re.sub(rf"\s+{re.escape(unit_upper)}$", "", cleaned)

    # Normaliza espaços resultantes e remove tokens vazios
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def clean_display_name(description: str, unit: str = "UN") -> str:
    """Limpa o nome de exibição de um produto, preservando a legibilidade.

    Remove sufixos de medida numérica e a unidade de medida quando esta
    aparece no final, mas mantém a caixa original e os acentos para
    exibição amigável.

    Args:
        description: Texto bruto da descrição do item.
        unit: Unidade de medida usada para remover sufixo final.

    Returns:
        Nome limpo para exibição, com sufixos de medida removidos.
    """
    if not description or not description.strip():
        return ""

    cleaned = description.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Remove medidas numéricas no final (ex: "LEITE INTEGRAL 1L", "PAO 500G")
    cleaned = _MEASURE_PATTERN.sub("", cleaned)

    # Remove a unidade informada quando aparecer como última palavra
    if unit:
        unit_clean = unit.strip().upper()
        cleaned = re.sub(rf"\s+{re.escape(unit_clean)}$", "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def guess_category(description: str) -> str | None:
    """Classifica a descrição de um produto em uma categoria do catálogo.

    Usa palavras-chave por categoria definidas em `_CATEGORY_KEYWORDS`.
    A busca é feita em caixa alta e sem acentos.

    Args:
        description: Descrição do produto (ex: "LEITE INTEGRAL 1L").

    Returns:
        Nome da categoria encontrada (ex: "laticínios") ou `None` se nenhuma
        palavra-chave for encontrada.
    """
    if not description:
        return None

    tokens = _tokenize(description)
    if not tokens:
        return None

    for category, keywords in _CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            # Palavras-chave podem ser compostas (ex: "CREME DE LEITE")
            keyword_tokens = _tokenize(keyword)
            if not keyword_tokens:
                continue
            # Verifica se todos os tokens da palavra-chave aparecem
            # em sequência na descrição
            for i in range(len(tokens) - len(keyword_tokens) + 1):
                if tokens[i : i + len(keyword_tokens)] == keyword_tokens:
                    return category

    return None
