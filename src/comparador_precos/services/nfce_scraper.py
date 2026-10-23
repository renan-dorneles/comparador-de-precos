# ============================================================
# src/comparador_precos/services/nfce_scraper.py
# ============================================================
"""Scraper de NFC-e da SEFAZ-RS: busca o HTML e extrai os dados da nota.

O portal da SEFAZ-RS (`nfce.sefaz.rs.gov.br`) devolve uma página HTML com:
  * uma tabela de identificação do emitente (CNPJ, razão social, endereço,
    data de emissão);
  * uma tabela de itens (código, descrição, quantidade, unidade, valores);
  * uma tabela de totais.

Como o layout pode mudar, a extração é *dirigida por rótulos* ("CNPJ",
"Data de Emissão", "Valor Total"...) e não por posições fixas, e a tabela de
itens é reconhecida pelo formato das linhas (quantidade numérica + unidade
alfabética + valor monetário).
"""

import re
from dataclasses import dataclass
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

from comparador_precos.core.config import get_settings

settings = get_settings()

# Rótulos aceitos para cada campo (comparados sem caixa)
CNPJ_LABELS = ("cnpj",)
STORE_NAME_LABELS = (
    "razão social",
    "razao social",
    "nome fantasia",
    "nome do emitente",
    "estabelecimento",
    "emitente",
)
ADDRESS_LABELS = ("endereço", "endereco", "logradouro")
ISSUE_DATE_LABELS = ("data de emissão", "data de emissao", "emissão", "emissao")
TOTAL_LABELS = ("valor total", "total da nota", "total", "total r$")

# Elementos que podem conter um rótulo
_LABEL_TAGS = ("td", "th", "span", "div", "p", "label", "b", "strong", "h1", "h2", "h3")

# Rótulos com mais de 60 caracteres não são rótulos (filtram wrappers grandes)
_MAX_LABEL_LENGTH = 60

_DATE_PATTERNS = ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d")
_CNPJ_PATTERN = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")
_UNIT_PATTERN = re.compile(r"^[A-Za-z]{1,5}$")


class NFCeScrapeError(Exception):
    """Levantada quando o HTML da SEFAZ não pôde ser interpretado."""


@dataclass(frozen=True)
class ScrapedItem:
    """Item de produto extraído da nota."""

    description: str
    quantity: float
    unit: str
    price: float


@dataclass(frozen=True)
class ScrapedStore:
    """Dados do emitente extraídos da nota."""

    name: str
    cnpj: str | None = None
    address: str | None = None


@dataclass(frozen=True)
class ScrapedInvoice:
    """Nota fiscal completa, extraída do HTML da SEFAZ."""

    access_key: str
    issue_date: datetime
    total_value: float
    store: ScrapedStore
    items: tuple[ScrapedItem, ...]
    raw_html: str
def build_consultation_url(access_key: str, base_url: str | None = None) -> str:
    """Monta a URL de consulta da NFC-e para uma chave de acesso."""
    base = (base_url or settings.sefaz_base_url).rstrip("/")
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}p={access_key}"


def _normalize_ws(text: str) -> str:
    """Normaliza espaços e quebras de linha."""
    return re.sub(r"\s+", " ", text or "").strip()


def _parse_decimal(raw: str) -> float | None:
    """Converte texto numérico pt-BR ('R$ 1.234,56') em float."""
    text = re.sub(r"[R$\s ]", "", raw or "")
    if not text:
        return None
    if "," in text:
        # Vírgula é o separador decimal; ponto é separador de milhar
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_date(raw: str) -> datetime | None:
    """Converte data pt-BR ('10/05/2023') em datetime."""
    text = _normalize_ws(raw)
    for pattern in _DATE_PATTERNS:
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def _is_date(value: str) -> bool:
    """True se o texto parece uma data."""
    return _parse_date(value) is not None


def _is_number(value: str) -> bool:
    """True se o texto é um número."""
    return _parse_decimal(value) is not None


def _has_cnpj(value: str) -> bool:
    """True se o texto contém um CNPJ."""
    return bool(_CNPJ_PATTERN.search(value))

def _extract_labeled(
    soup: BeautifulSoup,
    labels: tuple[str, ...],
    validator=None,
    exact: bool = False,
) -> str | None:
    """Encontra o valor associado a um dos rótulos informados.

    Procura, nesta ordem: texto após o rótulo na mesma célula ("Total: R$ 1,00"),
    célula irmã seguinte ("<td>Total</td><td>R$ 1,00</td>") e, por fim, a
    próxima célula da mesma linha.

    Args:
        soup: HTML já parseado
        labels: rótulos aceitos (comparados sem caixa)
        validator: callable opcional que valida o candidato encontrado
        exact: se True, o texto da célula deve ser *igual* ao rótulo, e não
            apenas começar com ele. Evita confundir "Total dos Produtos" com
            o total da nota.

    Returns:
        O texto do valor, ou None se nenhum rótulo produziu valor válido.
    """
    for element in _iter_label_candidates(soup):
        text = _normalize_ws(element.get_text(" ", strip=True))
        if not text or len(text) > _MAX_LABEL_LENGTH:
            continue

        for label in labels:
            if exact:
                if text.casefold() != label.casefold():
                    continue
                remainder = ""
            else:
                if not text.casefold().startswith(label.casefold()):
                    continue
                remainder = text[len(label) :].strip(" :\t-–—")

            candidates = [remainder] if remainder else []

            sibling = element.find_next_sibling()
            if sibling is not None:
                candidates.append(_normalize_ws(sibling.get_text(" ", strip=True)))

            row = element.find_parent("tr")
            if row is not None:
                cells = [
                    _normalize_ws(c.get_text(" ", strip=True)) for c in row.find_all("td")
                ]
                if text in cells:
                    index = cells.index(text)
                    if index + 1 < len(cells):
                        candidates.append(cells[index + 1])

            for candidate in candidates:
                if not candidate:
                    continue
                if validator is None or validator(candidate):
                    return candidate

    return None


def _select_unit_price(values: list[float], quantity: float) -> float:
    """Escolhe, entre os valores monetários da linha, o preço unitário."""
    if len(values) == 1:
        return values[0]

    best = values[0]
    best_error = float("inf")
    for candidate in values:
        for other in values:
            if candidate is other:
                continue
            error = abs(candidate * quantity - other)
            if error < best_error:
                best_error = error
                best = candidate
    return best


def _extract_items(soup: BeautifulSoup) -> tuple[ScrapedItem, ...]:
    """Extrai os itens da nota varrendo as linhas das tabelas.

    Uma linha é considerada de item quando possui: uma descrição textual, uma
    quantidade numérica, uma unidade alfabética curta e ao menos um valor
    monetário. A descrição é usada como âncora: os campos numéricos e a
    unidade são lidos *a partir dela*, o que evita confundir o código do
    produto com a quantidade.
    """
    items: list[ScrapedItem] = []

    for row in soup.find_all("tr"):
        cells = [_normalize_ws(c.get_text(" ", strip=True)) for c in row.find_all("td")]
        if len(cells) < 4:
            continue

        description_index = _find_description_index(cells)
        if description_index is None:
            continue

        after = cells[description_index + 1 :]
        if not after:
            continue

        quantity = _first_positive_number(after)
        if quantity is None:
            continue

        unit = next(
            (c.upper() for c in after if _UNIT_PATTERN.match(c) and len(c) <= 5 and c != "R$"),
            None,
        )
        if unit is None:
            continue

        money = [v for v in (_parse_decimal(c) for c in after) if v is not None and v > 0]
        money = [v for v in money if v != quantity]
        if not money:
            continue

        items.append(
            ScrapedItem(
                description=cells[description_index],
                quantity=quantity,
                unit=unit,
                price=_select_unit_price(money, quantity),
            )
        )

    return tuple(items)


def _find_description_index(cells: list[str]) -> int | None:
    """Índice da célula com a descrição do item (texto mais longo não numérico)."""
    best_index: int | None = None
    best_length = 0
    for index, cell in enumerate(cells):
        if not cell or _parse_decimal(cell) is not None:
            continue
        if len(cell) > best_length:
            best_length = len(cell)
            best_index = index
    if best_index is None or best_length < 2:
        return None
    return best_index


def _first_positive_number(cells: list[str]) -> float | None:
    """Primeiro número positivo de uma lista de células."""
    for cell in cells:
        value = _parse_decimal(cell)
        if value is not None and value > 0:
            return value
    return None


def _iter_label_candidates(soup: BeautifulSoup) -> list[Tag]:
    """Elementos que podem conter um rótulo, do mais específico ao mais genérico."""
    elements = [el for el in soup.find_all(_LABEL_TAGS) if isinstance(el, Tag)]
    # Elementos mais profundos primeiro: um <td> é melhor que o <div> que o contém
    elements.sort(key=lambda el: len(list(el.parents)), reverse=True)
    return elements

def parse_invoice_html(html: str, access_key: str) -> ScrapedInvoice:
    """Extrai os dados da nota a partir do HTML da SEFAZ.

    Args:
        html: HTML bruto retornado pela SEFAZ-RS
        access_key: Chave de acesso de 44 dígitos da nota

    Returns:
        ScrapedInvoice com os dados extraídos

    Raises:
        NFCeScrapeError: Se o HTML estiver vazio ou não permitir extrair
            data de emissão, total ou itens.
    """
    if not html or not html.strip():
        raise NFCeScrapeError("HTML da SEFAZ vazio")

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:  # pragma: no cover - lxml ausente/corrompido
        soup = BeautifulSoup(html, "html.parser")

    issue_date_raw = _extract_labeled(soup, ISSUE_DATE_LABELS, validator=_is_date)
    issue_date = _parse_date(issue_date_raw) if issue_date_raw else None
    if issue_date is None:
        raise NFCeScrapeError("Data de emissão não encontrada no HTML da SEFAZ")

    total_raw = _extract_labeled(soup, ("valor total", "total da nota"), validator=_is_number)
    if total_raw is None:
        # "Total" exato: evita capturar subtotais como "Total dos Produtos"
        total_raw = _extract_labeled(soup, ("total",), validator=_is_number, exact=True)
    total_value = _parse_decimal(total_raw) if total_raw else None
    if total_value is None:
        raise NFCeScrapeError("Valor total não encontrado no HTML da SEFAZ")

    items = _extract_items(soup)
    if not items:
        raise NFCeScrapeError("Nenhum item encontrado no HTML da SEFAZ")

    cnpj_raw = _extract_labeled(soup, CNPJ_LABELS, validator=_has_cnpj)
    cnpj_match = _CNPJ_PATTERN.search(cnpj_raw) if cnpj_raw else None
    cnpj = cnpj_match.group(0) if cnpj_match else None

    name = _extract_labeled(soup, STORE_NAME_LABELS)
    if not name:
        raise NFCeScrapeError("Razão social do emitente não encontrada no HTML da SEFAZ")

    address = _extract_labeled(soup, ADDRESS_LABELS)

    return ScrapedInvoice(
        access_key=access_key,
        issue_date=issue_date,
        total_value=total_value,
        store=ScrapedStore(name=name, cnpj=cnpj, address=address),
        items=items,
        raw_html=html,
    )


async def fetch_invoice_html(
    access_key: str,
    *,
    base_url: str | None = None,
    timeout: float = 15.0,
    client: httpx.AsyncClient | None = None,
) -> str:
    """Busca o HTML da nota na SEFAZ-RS.

    Args:
        access_key: Chave de acesso de 44 dígitos
        base_url: URL base do portal (padrão: settings.sefaz_base_url)
        timeout: Timeout da requisição em segundos
        client: Cliente httpx opcional (útil em testes)

    Returns:
        HTML bruto da página de consulta

    Raises:
        NFCeScrapeError: Se a requisição falhar ou retornar erro HTTP.
    """
    url = build_consultation_url(access_key, base_url=base_url)

    if client is not None:
        response = await client.get(url, timeout=timeout)
    else:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "comparador-de-precos/0.1 (+crowdsourcing NFC-e)"},
        ) as own_client:
            response = await own_client.get(url)

    if response.status_code >= 400:
        raise NFCeScrapeError(
            f"SEFAZ-RS respondeu HTTP {response.status_code} para a chave {access_key}"
        )

    return response.text


async def scrape_invoice(
    access_key: str,
    *,
    base_url: str | None = None,
    timeout: float = 15.0,
    client: httpx.AsyncClient | None = None,
) -> ScrapedInvoice:
    """Busca e interpreta a nota na SEFAZ-RS.

    Args:
        access_key: Chave de acesso de 44 dígitos
        base_url: URL base do portal
        timeout: Timeout da requisição em segundos
        client: Cliente httpx opcional (útil em testes)

    Returns:
        ScrapedInvoice com os dados extraídos

    Raises:
        NFCeScrapeError: Se a requisição ou a extração falhar.
    """
    html = await fetch_invoice_html(
        access_key, base_url=base_url, timeout=timeout, client=client
    )
    return parse_invoice_html(html, access_key)

