"""Testes unitários do scraper de NFC-e (SEFAZ-RS)."""

from datetime import datetime
from pathlib import Path

import pytest

from comparador_precos.services.nfce_scraper import (
    NFCeScrapeError,
    build_consultation_url,
    parse_invoice_html,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "nfce_sefaz_rs.html"
CHAVE = "43230512345678000190650010000000011000000014"


@pytest.fixture
def html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


class TestParseInvoiceHtml:
    def test_extrai_chave_e_dados_principais(self, html):
        nota = parse_invoice_html(html, CHAVE)

        assert nota.access_key == CHAVE
        assert nota.issue_date == datetime(2023, 5, 10)
        assert nota.total_value == pytest.approx(41.33)

    def test_extrai_dados_da_loja(self, html):
        loja = parse_invoice_html(html, CHAVE).store

        assert loja.name == "Supermercados Exemplo Ltda"
        assert loja.cnpj == "12.345.678/0001-90"
        assert loja.address == "Rua das Flores, 123 - Centro"

    def test_extrai_itens_com_quantidade_unidade_e_preco_unitario(self, html):
        itens = parse_invoice_html(html, CHAVE).items

        assert len(itens) == 3
        assert itens[0].description == "LEITE INTEGRAL 1L"
        assert itens[0].quantity == pytest.approx(2)
        assert itens[0].unit == "UN"
        # Preço unitário, não o total da linha
        assert itens[0].price == pytest.approx(4.99)

    def test_preserva_quantidade_fracionada(self, html):
        itens = parse_invoice_html(html, CHAVE).items

        assert itens[1].description == "PAO FRANCES KG"
        assert itens[1].quantity == pytest.approx(0.5)
        assert itens[1].unit == "KG"
        assert itens[1].price == pytest.approx(12.90)

    def test_preserva_html_bruto(self, html):
        assert parse_invoice_html(html, CHAVE).raw_html == html

    def test_html_sem_itens_levanta_erro(self):
        html_sem_itens = "<html><body><p>Nada aqui</p></body></html>"

        with pytest.raises(NFCeScrapeError):
            parse_invoice_html(html_sem_itens, CHAVE)

    def test_html_vazio_levanta_erro(self):
        with pytest.raises(NFCeScrapeError):
            parse_invoice_html("", CHAVE)

    def test_html_sem_data_de_emissao_levanta_erro(self, html):
        sem_data = html.replace("Data de Emissão", "Outro Campo")

        with pytest.raises(NFCeScrapeError):
            parse_invoice_html(sem_data, CHAVE)

    def test_html_sem_total_levanta_erro(self, html):
        sem_total = html.replace("Valor Total", "Outra Coisa")

        with pytest.raises(NFCeScrapeError):
            parse_invoice_html(sem_total, CHAVE)


class TestBuildConsultationUrl:
    def test_monta_url_com_chave(self):
        url = build_consultation_url(CHAVE, base_url="https://sefaz.example/nfce")

        assert url.startswith("https://sefaz.example/nfce")
        assert CHAVE in url

    def test_usa_parametro_p_por_padrao(self):
        url = build_consultation_url(CHAVE, base_url="https://sefaz.example/nfce")

        assert f"p={CHAVE}" in url
