# ============================================================
# src/comparador_precos/api/routes/invoices.py
# ============================================================
"""Rotas para ingestão e consulta de NFC-e."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from comparador_precos.api.routes.auth import get_current_user
from comparador_precos.core.database import get_session
from comparador_precos.models.invoice import Invoice
from comparador_precos.models.user import User
from comparador_precos.schemas.invoice import (
    InvoiceRead,
    InvoiceScanRequest,
    InvoiceScanResponse,
)
from comparador_precos.services.ingestion import (
    DuplicateInvoiceError,
    IngestionError,
    InvoiceTooOldError,
    RateLimitExceededError,
    ingest_nfce,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post(
    "/scan",
    response_model=InvoiceScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Processa QR Code de NFC-e",
    description=(
        "Recebe a URL do QR Code (ou chave de acesso), busca a nota na SEFAZ-RS, "
        "valida, mapeia itens para o catálogo e salva no banco. "
        "Concede 5 créditos ao usuário se processada com sucesso."
    ),
)
async def scan_invoice(
    request: InvoiceScanRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InvoiceScanResponse:
    """Processa uma NFC-e via QR Code.

    Fluxo:
    1. Extrai a chave de acesso (44 dígitos) da URL
    2. Verifica duplicidade (retorna 200 se já existe)
    3. Verifica rate limit (3 scans/dia)
    4. Busca HTML na SEFAZ-RS
    5. Valida data de emissão (<= 7 dias)
    6. Mapeia itens para catálogo genérico
    7. Salva tudo em transação atômica + concede 5 créditos

    Args:
        request: JSON com campo `qr_code` (URL ou chave pura)
        db: Sessão do banco
        current_user: Usuário autenticado

    Returns:
        InvoiceScanResponse com dados da nota processada ou status
    """
    try:
        invoice = await ingest_nfce(db, current_user, request.qr_code)
    except DuplicateInvoiceError as e:
        return InvoiceScanResponse(
            status="duplicate",
            message=f"Nota fiscal {e.access_key} já cadastrada",
            invoice=None,
            credits_earned=0,
        )
    except InvoiceTooOldError as e:
        return InvoiceScanResponse(
            status="too_old",
            message=f"Nota muito antiga (emissão: {e.issue_date.date()})",
            invoice=None,
            credits_earned=0,
        )
    except RateLimitExceededError:
        return InvoiceScanResponse(
            status="rate_limited",
            message="Limite diário de 3 cupons atingido",
            invoice=None,
            credits_earned=0,
        )
    except IngestionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return InvoiceScanResponse(
        status="success",
        message="Nota fiscal processada com sucesso",
        invoice=InvoiceRead.model_validate(invoice),
        credits_earned=5,
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceRead,
    summary="Busca nota fiscal por ID",
)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InvoiceRead:
    """Busca uma nota fiscal pelo ID."""
    from sqlalchemy import select

    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.user_id == current_user.id)
    )
    invoice = result.scalar_one_or_none()

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada",
        )

    return InvoiceRead.model_validate(invoice)