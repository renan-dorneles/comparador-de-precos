# ============================================================
# src/comparador_precos/services/nfce_decoder.py
# ============================================================
"""Decoder de QR Code NFC-e: extração e validação da chave de acesso SEFAZ.

A chave de acesso NFC-e é composta por 44 dígitos:
    cUF(2) + AAMM(4) + CNPJ(14) + mod(2) + serie(3) + nNF(9) + tpEmis(1)
    + cDV(1) + tpAmb(1) + cNF(1) + cDV(1) + cIdToken(1) + nDigVal(1) + digVal(4)

A URL do QR Code da SEFAZ tem o formato:
    https://www.nfce.sefaz.rs.gov.br/nfce-web/pages/QRCode.aspx?p=<CHAVE>
    ...ou em formato genérico: ?chNFe=<CHAVE>&nVersao=100
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

# Parâmetros de query que podem conter a chave de acesso
_QUERY_KEYS = ("p", "chNFe", "chave", "nChave")

# Padrão de 44 dígitos
_ACCESS_KEY_PATTERN = re.compile(r"^\d{44}$")

# Dígitos que aparecem em qualquer URL (evita falso positivo em query strings)
_DIGIT_RUN = re.compile(r"\d{44}")


class NFCeDecodeError(Exception):
    """Levantada quando o QR Code não contém uma chave de acesso válida."""


@dataclass(frozen=True)
class AccessKey:
    """Chave de acesso SEFAZ decomposta."""

    key: str
    uf: str
    year: int
    month: int
    cnpj: str
    model: str
    series: str
    document_number: str
    emission_type: str
    environment: str
    issued_at: datetime

    @property
    def is_contingency(self) -> bool:
        """True se o tipo de emissão for contingência (tpEmis = 2, 4, 6, 7, 9)."""
        return self.emission_type in {"2", "4", "6", "7", "9"}


def extract_access_key(qr_content: str) -> str:
    """Extrai a chave de acesso de 44 dígitos de um QR Code NFC-e.

    Aceita:
      * URL completa da SEFAZ com a chave em query string
      * A chave de acesso pura (44 dígitos)

    Args:
        qr_content: Conteúdo bruto lido do QR Code

    Returns:
        A chave de acesso de 44 dígitos

    Raises:
        NFCeDecodeError: Se não for possível extrair uma chave válida
    """
    if not qr_content or not qr_content.strip():
        raise NFCeDecodeError("QR Code vazio")

    conteudo = qr_content.strip()

    # Caso 1: a chave já veio pura
    if _ACCESS_KEY_PATTERN.match(conteudo):
        return conteudo

    # Caso 2: extrai da URL (parâmetros conhecidos)
    for chave_param in _QUERY_KEYS:
        match = re.search(rf"[?&]{re.escape(chave_param)}=(\d{{44}})", conteudo)
        if match:
            return match.group(1)

    # Caso 3: qualquer sequência de 44 dígitos na URL
    match = _DIGIT_RUN.search(conteudo)
    if match:
        return match.group(0)

    raise NFCeDecodeError("Chave de acesso de 44 dígitos não encontrada no QR Code")


def parse_access_key(access_key: str) -> AccessKey:
    """Decompõe a chave de acesso SEFAZ em seus componentes.

    Args:
        access_key: Chave de 44 dígitos

    Returns:
        AccessKey com os campos decompostos

    Raises:
        NFCeDecodeError: Se a chave não tiver 44 dígitos
    """
    if not _ACCESS_KEY_PATTERN.match(access_key or ""):
        raise NFCeDecodeError("Chave de acesso deve ter exatamente 44 dígitos")

    uf = access_key[0:2]
    ano = int(access_key[2:4])
    mes = int(access_key[4:6])
    cnpj = access_key[6:20]
    modelo = access_key[20:22]
    serie = access_key[22:25]
    numero = access_key[25:34]
    tipo_emissao = access_key[34:35]
    ambiente = access_key[35:36]

    if not 1 <= mes <= 12:
        raise NFCeDecodeError(f"Mês inválido na chave de acesso: {mes}")

    try:
        emitido_em = datetime(2000 + ano, mes, 1)
    except ValueError as exc:  # pragma: no cover - protegido pela validação do mês
        raise NFCeDecodeError(f"Data inválida na chave de acesso: {exc}") from exc

    return AccessKey(
        key=access_key,
        uf=uf,
        year=2000 + ano,
        month=mes,
        cnpj=cnpj,
        model=modelo,
        series=serie,
        document_number=numero,
        emission_type=tipo_emissao,
        environment=ambiente,
        issued_at=emitido_em,
    )


def decode_qr_code(qr_content: str) -> AccessKey:
    """Faz o pipeline completo: extrai e decompõe a chave de acesso.

    Args:
        qr_content: Conteúdo bruto do QR Code

    Returns:
        AccessKey decomposta

    Raises:
        NFCeDecodeError: Se o QR Code for inválido
    """
    return parse_access_key(extract_access_key(qr_content))


def is_expired(
    issue_date: datetime,
    max_age_days: int = 7,
    now: datetime | None = None,
) -> bool:
    """Verifica se a nota fiscal está fora da validade.

    Regra antifraude (docs/README.md): apenas notas emitidas nos últimos
    7 dias são válidas para pontuação e armazenamento.

    Args:
        issue_date: Data de emissão da nota
        max_age_days: Idade máxima aceita em dias
        now: Momento de referência (padrão: agora). Útil para testes.

    Returns:
        True se a nota for antiga demais
    """
    referencia = now or datetime.now(issue_date.tzinfo)
    return (referencia - issue_date) > timedelta(days=max_age_days)
