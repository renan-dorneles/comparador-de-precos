# ============================================================
# tests/unit/test_nfce_decoder.py
# ============================================================
"""Testes unitários do decoder de QR Code NFC-e."""

from datetime import datetime, timedelta

import pytest

from comparador_precos.services.nfce_decoder import (
    NFCeDecodeError,
    decode_qr_code,
    extract_access_key,
    is_expired,
    parse_access_key,
)

# Chave de acesso válida de exemplo (44 dígitos)
# UF=43 (RS), AAMM=2305, CNPJ=00000000000191, mod=65, serie=1, nNF=123,
# tpEmis=1, cDV=0, tpAmb=1, cNF=1, cDV=0, cIdToken=0, nDigVal=1, digVal=4
CHAVE_VALIDA = "43230500000000000191650010000000011000000014"


class TestExtractAccessKey:
    def test_extract_from_sefaz_url(self):
        url = (
            "https://www.nfce.sefaz.rs.gov.br/nfce-web/pages/QRCode.aspx"
            f"?p={CHAVE_VALIDA}"
        )

        assert extract_access_key(url) == CHAVE_VALIDA

    def test_extract_from_generic_url_with_chNFe(self):
        url = f"https://example.com/nfce?chNFe={CHAVE_VALIDA}&nVersao=100"

        assert extract_access_key(url) == CHAVE_VALIDA

    def test_extract_from_plain_key(self):
        assert extract_access_key(CHAVE_VALIDA) == CHAVE_VALIDA

    def test_extract_with_surrounding_whitespace(self):
        assert extract_access_key(f"  {CHAVE_VALIDA}\n") == CHAVE_VALIDA

    def test_extract_finds_key_in_arbitrary_url(self):
        url = f"https://app.exemplo.com/scan/ref/12345?data={CHAVE_VALIDA}&x=1"

        assert extract_access_key(url) == CHAVE_VALIDA

    @pytest.mark.parametrize("conteudo", ["", "   ", "nao tem chave nenhuma"])
    def test_invalid_content_raises(self, conteudo):
        with pytest.raises(NFCeDecodeError):
            extract_access_key(conteudo)

    def test_wrong_length_raises(self):
        with pytest.raises(NFCeDecodeError):
            extract_access_key("1234567890123456789012345678901234567890123")


class TestParseAccessKey:
    def test_decomposes_all_fields(self):
        resultado = parse_access_key(CHAVE_VALIDA)

        assert resultado.key == CHAVE_VALIDA
        assert resultado.uf == "43"
        assert resultado.year == 2023
        assert resultado.month == 5
        assert resultado.cnpj == "00000000000191"
        assert resultado.model == "65"
        assert resultado.series == "001"
        assert resultado.document_number == "000000001"
        assert resultado.emission_type == "1"
        assert resultado.environment == "0"
        assert resultado.issued_at == datetime(2023, 5, 1)

    def test_contingency_emission_detected(self):
        chave_contingencia = CHAVE_VALIDA[:34] + "9" + CHAVE_VALIDA[35:]

        resultado = parse_access_key(chave_contingencia)

        assert resultado.is_contingency is True

    def test_normal_emission_not_contingency(self):
        assert parse_access_key(CHAVE_VALIDA).is_contingency is False

    @pytest.mark.parametrize("chave", ["123", "", "abc" * 15, CHAVE_VALIDA[:-1]])
    def test_invalid_key_raises(self, chave):
        with pytest.raises(NFCeDecodeError):
            parse_access_key(chave)

    def test_invalid_month_raises(self):
        chave_mes_13 = CHAVE_VALIDA[:4] + "13" + CHAVE_VALIDA[6:]

        with pytest.raises(NFCeDecodeError):
            parse_access_key(chave_mes_13)


class TestDecodeQrCode:
    def test_full_pipeline(self):
        url = (
            "https://www.nfce.sefaz.rs.gov.br/nfce-web/pages/QRCode.aspx"
            f"?p={CHAVE_VALIDA}"
        )

        resultado = decode_qr_code(url)

        assert resultado.key == CHAVE_VALIDA
        assert resultado.uf == "43"


class TestIsExpired:
    def test_recent_invoice_is_not_expired(self):
        agora = datetime.now()

        assert is_expired(agora - timedelta(days=3), max_age_days=7) is False

    def test_invoice_older_than_seven_days_is_expired(self):
        agora = datetime.now()

        assert is_expired(agora - timedelta(days=8), max_age_days=7) is True

    def test_exactly_seven_days_is_not_expired(self):
        """Limite é inclusivo: exatamente 7 dias ainda é válido."""
        referencia = datetime.now()
        emissao = referencia - timedelta(days=7)

        assert is_expired(emissao, max_age_days=7, now=referencia) is False

    def test_future_date_is_not_expired(self):
        futuro = datetime.now() + timedelta(days=1)

        assert is_expired(futuro, max_age_days=7) is False