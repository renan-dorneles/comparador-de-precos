# ============================================================
# src/comparador_precos/services/ingestion.py
# ============================================================
"""Serviço de orquestração do pipeline de ingestão NFC-e.

Fluxo completo da Fase 3 (conforme ARCHITECTURE.md):
1. Decode & Extract: extrair chave de acesso do QR Code
2. Check Duplication: consultar BD por access_key existente
3. Scrape HTML: buscar HTML na SEFAZ-RS
4. Time Validation: validar se nota tem <= 7 dias
5. AI Processing: mapear itens para catálogo genérico
6. Database Commit: transação atômica (Invoice + Items + StorePrice + Ledger)
"""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comparador_precos.core.config import get_settings
from comparador_precos.models.credit_transaction import (
    CreditTransaction,
    TransactionType,
)
from comparador_precos.models.invoice import Invoice, InvoiceItem
from comparador_precos.models.product_catalog import ProductCatalog
from comparador_precos.models.store import Store, StorePrice
from comparador_precos.models.user import User
from comparador_precos.services.catalog_matcher import (
    clean_display_name,
    guess_category,
    normalize_description,
)
from comparador_precos.services.ledger import LedgerService
from comparador_precos.services.nfce_decoder import NFCeDecodeError, decode_qr_code
from comparador_precos.services.nfce_scraper import (
    NFCeScrapeError,
    fetch_invoice_html,
    parse_invoice_html,
)

settings = get_settings()


class IngestionError(Exception):
    """Erro genérico do pipeline de ingestão."""


class DuplicateInvoiceError(IngestionError):
    """Levantada quando a nota fiscal já existe no banco."""

    def __init__(self, access_key: str) -> None:
        self.access_key = access_key
        super().__init__(f"Nota fiscal {access_key} já cadastrada")


class InvoiceTooOldError(IngestionError):
    """Levantada quando a nota tem mais de 7 dias."""

    def __init__(self, issue_date: datetime) -> None:
        self.issue_date = issue_date
        super().__init__(f"Nota muito antiga (emissão: {issue_date.date()})")


class RateLimitExceededError(IngestionError):
    """Levantada quando o usuário excede o limite de 3 scans/dia."""

    def __init__(self) -> None:
        super().__init__("Limite diário de 3 cupons atingido")


async def check_rate_limit(db: AsyncSession, user_id: int) -> bool:
    """Verifica se o usuário pode fazer mais um scan hoje (limite: 3/dia)."""
    from sqlalchemy import func

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(CreditTransaction.id)).where(
            CreditTransaction.user_id == user_id,
            CreditTransaction.transaction_type == TransactionType.SCAN_REWARD,
            CreditTransaction.created_at >= today_start,
        )
    )
    count = result.scalar() or 0
    return count < 3


async def get_or_create_store(
    db: AsyncSession, scraped_store, access_key: str
) -> Store:
    """Busca ou cria uma loja no banco baseada nos dados do scrape."""
    if scraped_store.cnpj:
        result = await db.execute(
            select(Store).where(Store.cnpj == scraped_store.cnpj)
        )
        store = result.scalar_one_or_none()
        if store:
            return store

    result = await db.execute(
        select(Store).where(Store.name == scraped_store.name)
    )
    store = result.scalar_one_or_none()
    if store:
        if scraped_store.cnpj and not store.cnpj:
            store.cnpj = scraped_store.cnpj
        return store

    store = Store(
        name=scraped_store.name,
        cnpj=scraped_store.cnpj,
        address=scraped_store.address,
    )
    db.add(store)
    await db.flush()
    return store


async def get_or_create_catalog_product(
    db: AsyncSession,
    scraped_description: str,
    unit: str,
) -> ProductCatalog:
    """Busca ou cria um produto no catálogo genérico."""
    normalized = normalize_description(scraped_description, unit)
    if not normalized:
        normalized = clean_display_name(scraped_description, unit)

    result = await db.execute(
        select(ProductCatalog).where(
            ProductCatalog.generic_name == normalized
        )
    )
    catalog_product = result.scalar_one_or_none()
    if catalog_product:
        return catalog_product

    category = guess_category(normalized or scraped_description)
    catalog_product = ProductCatalog(
        generic_name=normalized,
        category=category,
        unit_of_measure=unit,
    )
    db.add(catalog_product)
    await db.flush()
async def process_invoice_items(
    db: AsyncSession,
    invoice: Invoice,
    scraped_items,
    store_id: int,
) -> list[InvoiceItem]:
    """Processa os itens da nota, criando InvoiceItems e vinculando ao catálogo."""
    items = []
    for scraped_item in scraped_items:
        catalog_product = await get_or_create_catalog_product(
            db,
            scraped_item.description,
            scraped_item.unit,
        )
        item = InvoiceItem(
            invoice_id=invoice.id,
            description=scraped_item.description,
            quantity=scraped_item.quantity,
            unit=scraped_item.unit,
            price=scraped_item.price,
            catalog_product_id=catalog_product.id,
        )
        db.add(item)
        items.append(item)

        store_price = StorePrice(
            store_id=store_id,
            catalog_product_id=catalog_product.id,
            price=scraped_item.price,
            invoice_item_id=item.id,
        )
        db.add(store_price)

    await db.flush()
    return items


async def ingest_nfce(
    db: AsyncSession,
    user: User,
    qr_code_content: str,
) -> Invoice:
    """Pipeline completo de ingestão de uma NFC-e.

    Implementa o fluxo da ARCHITECTURE.md Fase 3:
    1. Decode & Extract: extrair chave de 44 dígitos
    2. Check Duplication: consultar BD por access_key
    3. Scrape HTML: buscar na SEFAZ-RS
    4. Time Validation: validar data <= 7 dias
    5. AI Processing: mapear itens para catálogo
    6. Database Commit: transação atômica com ledger

    Args:
        db: Sessão do banco (transação já iniciada)
        user: Usuário autenticado
        qr_code_content: URL do QR Code ou chave de acesso

    Returns:
        Invoice criada

    Raises:
        DuplicateInvoiceError: Se nota já existe
        InvoiceTooOldError: Se nota tem > 7 dias
        RateLimitExceededError: Se usuário excedeu limite diário
        IngestionError: Outros erros do pipeline
    """
    # 1. Decode & Extract
    try:
        decoded = decode_qr_code(qr_code_content)
        access_key = decoded.key
    except NFCeDecodeError as e:
        raise IngestionError(f"QR Code inválido: {e}")

    # 2. Check Duplication
    result = await db.execute(
        select(Invoice).where(Invoice.access_key == access_key)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise DuplicateInvoiceError(access_key)

    # 3. Rate Limit Check
    if not await check_rate_limit(db, user.id):
        raise RateLimitExceededError()

    # 4. Scrape HTML (busca na SEFAZ-RS)
    try:
        html = await fetch_invoice_html(access_key)
        scraped = parse_invoice_html(html, access_key)
    except NFCeScrapeError as e:
        raise IngestionError(f"Erro ao buscar/processar nota na SEFAZ: {e}")

    # 5. Time Validation (7 dias)
    now = datetime.now(scraped.issue_date.tzinfo)
    if scraped.issue_date < now - timedelta(days=7):
        raise InvoiceTooOldError(scraped.issue_date)

    # 6. Busca/cria loja
    store = await get_or_create_store(db, scraped.store, access_key)

    # 7. Cria Invoice (sem store_id - a associação é via StorePrice/InvoiceItem depois)
    invoice = Invoice(
        access_key=access_key,
        issue_date=scraped.issue_date,
        total_value=scraped.total_value,
        user_id=user.id,
        raw_html=scraped.raw_html,
    )
    db.add(invoice)
    await db.flush()

    # 8. Processa itens (cria InvoiceItems + vincula catálogo + StorePrice)
    await process_invoice_items(db, invoice, scraped.items, store.id)

    # 9. Commit atômico: Invoice + Items + StorePrice + Ledger (+5 créditos)
    ledger = LedgerService(db)
    await ledger.add_credits(
        user_id=user.id,
        amount=5,
        transaction_type=TransactionType.SCAN_REWARD,
        reference_id=access_key,
    )

    return invoice
    return catalog_product