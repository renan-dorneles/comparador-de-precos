"""Testes unitários do mapeamento de descrições para o catálogo genérico."""

import pytest

from comparador_precos.services.catalog_matcher import (
    clean_display_name,
    guess_category,
    normalize_description,
)


class TestNormalizeDescription:
    def test_remove_medida_numerica(self):
        assert normalize_description("LEITE INTEGRAL 1L", "UN") == "LEITE INTEGRAL"

    def test_remove_medida_com_decimal(self):
        assert normalize_description("LEITE INTEGRAL 1,5L", "UN") == "LEITE INTEGRAL"

    def test_remove_unidade_no_final(self):
        assert normalize_description("PAO FRANCES KG", "KG") == "PAO FRANCES"

    def test_remove_acentos(self):
        assert normalize_description("PÃO FRANCÊS", "KG") == "PAO FRANCES"

    def test_normaliza_caixa_e_espacos(self):
        assert normalize_description("  arroz   agulHinha  ", "KG") == "ARROZ AGULHINHA"

    def test_mantem_nome_quando_unidade_nao_aparece(self):
        assert normalize_description("ARROZ AGULHINHA", "KG") == "ARROZ AGULHINHA"

    def test_descricao_vazia_devolve_vazio(self):
        assert normalize_description("", "UN") == ""


class TestCleanDisplayName:
    def test_remove_sufixo_de_medida(self):
        assert clean_display_name("LEITE INTEGRAL 1L", "UN") == "LEITE INTEGRAL"

    def test_remove_unidade_no_final(self):
        assert clean_display_name("PAO FRANCES KG", "KG") == "PAO FRANCES"

    def test_preserva_nome_legivel(self):
        assert clean_display_name("Arroz Agulhinha Tipo 1", "KG") == "Arroz Agulhinha Tipo 1"


class TestGuessCategory:
    @pytest.mark.parametrize(
        ("descricao", "esperada"),
        [
            ("LEITE INTEGRAL 1L", "laticínios"),
            ("QUEIJO MUSSARELA", "laticínios"),
            ("PAO FRANCES KG", "padaria"),
            ("REFRIGERANTE COCA COLA 2L", "bebidas"),
            ("DETERGENTE NEUTRO", "limpeza"),
            ("CARNE BOVINA CONGELADA", "acougue"),
            ("BANANA PRATA", "hortifruti"),
            ("ARROZ AGULHINHA 5KG", "mercearia"),
        ],
    )
    def test_classifica_produtos_conhecidos(self, descricao, esperada):
        assert guess_category(descricao) == esperada

    def test_produto_desconhecido_sem_categoria(self):
        assert guess_category("OBJETO SEM NOME CONHECIDO XYZ") is None
