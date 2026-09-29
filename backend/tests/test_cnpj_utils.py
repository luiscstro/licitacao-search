"""Testes unitários pro módulo cnpj_utils: validação de dígito verificador,
extração de dados, cache em memória e rate limiting. As chamadas de rede
são sempre mockadas — nenhum teste aqui bate na BrasilAPI/MinhaReceita de
verdade (isso foi verificado manualmente contra CNPJs reais durante o
desenvolvimento, não faz parte da suíte automatizada pra não deixá-la
dependente de rede)."""

import time
from unittest.mock import MagicMock

import pytest

from app import cnpj_utils

CNPJ_VALIDO = "00.000.000/0001-91"  # Banco do Brasil — CNPJ real, dígitos verificados
CNPJ_VALIDO_LIMPO = "00000000000191"


@pytest.fixture(autouse=True)
def _estado_isolado(monkeypatch):
    """O cache e o controle de rate limit são estado global do módulo —
    sem isolar, um teste vazaria pro próximo (inclusive fazendo o próximo
    esperar o intervalo mínimo por causa de uma chamada anterior). Também
    reduz o intervalo mínimo pra manter a suíte rápida; o teste dedicado ao
    rate limiter ajusta esse valor de novo pra verificar o comportamento real."""
    cnpj_utils._cache.clear()
    cnpj_utils._ultima_chamada.update(dict.fromkeys(cnpj_utils._ultima_chamada, 0.0))
    monkeypatch.setattr(cnpj_utils, "INTERVALO_MINIMO_SEGUNDOS", 0.01)
    yield
    cnpj_utils._cache.clear()
    cnpj_utils._ultima_chamada.update(dict.fromkeys(cnpj_utils._ultima_chamada, 0.0))


def _resposta_ok(corpo):
    resp = MagicMock(status_code=200)
    resp.json.return_value = corpo
    return resp


def _resposta_erro(status_code=404):
    return MagicMock(status_code=status_code)


class TestCnpjValido:
    def test_cnpjs_reais_sao_validos(self):
        # Banco do Brasil, Petrobras, Correios, Vale — CNPJs reais e públicos.
        for cnpj in ["00000000000191", "33000167000101", "34028316000103", "33592510000154"]:
            assert cnpj_utils._cnpj_valido(cnpj) is True, cnpj

    def test_todos_os_digitos_iguais_e_invalido_mesmo_com_tamanho_certo(self):
        assert cnpj_utils._cnpj_valido("00000000000000") is False
        assert cnpj_utils._cnpj_valido("11111111111111") is False

    def test_digito_verificador_errado_e_invalido(self):
        assert cnpj_utils._cnpj_valido("00000000000192") is False

    def test_tamanho_errado_e_invalido(self):
        assert cnpj_utils._cnpj_valido("1234567890123") is False
        assert cnpj_utils._cnpj_valido("123456789012345") is False
        assert cnpj_utils._cnpj_valido("") is False


class TestExtrairDados:
    def test_extrai_campos_com_os_nomes_usados_pelas_duas_apis(self):
        dados = cnpj_utils._extrair_dados(
            {
                "razao_social": "Empresa X",
                "descricao_situacao_cadastral": "ATIVA",
                "logradouro": "Rua A",
                "numero": "100",
                "complemento": "Sala 1",
                "bairro": "Centro",
                "municipio": "São Luís",
                "uf": "MA",
                "cep": "65000-000",
            }
        )
        assert dados == {
            "razao_social": "Empresa X",
            "situacao_cadastral": "ATIVA",
            "endereco_logradouro": "Rua A",
            "endereco_numero": "100",
            "endereco_complemento": "Sala 1",
            "endereco_bairro": "Centro",
            "endereco_cidade": "São Luís",
            "endereco_uf": "MA",
            "endereco_cep": "65000-000",
        }

    def test_campos_ausentes_viram_string_vazia(self):
        dados = cnpj_utils._extrair_dados({})
        assert all(valor == "" for valor in dados.values())


class TestBuscarDadosCnpj:
    def test_cnpj_invalido_levanta_value_error(self):
        with pytest.raises(ValueError):
            cnpj_utils.buscar_dados_cnpj("123")
        with pytest.raises(ValueError):
            cnpj_utils.buscar_dados_cnpj("11111111111111")

    def test_busca_com_sucesso_na_brasilapi_sem_precisar_da_minhareceita(self, monkeypatch):
        mock_get = MagicMock(
            return_value=_resposta_ok({"razao_social": "BB", "descricao_situacao_cadastral": "ATIVA"})
        )
        monkeypatch.setattr(cnpj_utils.requests, "get", mock_get)

        resultado = cnpj_utils.buscar_dados_cnpj(CNPJ_VALIDO)
        assert resultado["razao_social"] == "BB"
        assert mock_get.call_count == 1
        assert "brasilapi.com.br" in mock_get.call_args[0][0]

    def test_cai_pra_minhareceita_quando_brasilapi_falha(self, monkeypatch):
        respostas = [
            cnpj_utils.requests.RequestException("brasilapi fora do ar"),
            _resposta_ok({"razao_social": "BB via minhareceita", "descricao_situacao_cadastral": "ATIVA"}),
        ]

        def fake_get(url, *args, **kwargs):
            proxima = respostas.pop(0)
            if isinstance(proxima, Exception):
                raise proxima
            return proxima

        monkeypatch.setattr(cnpj_utils.requests, "get", fake_get)
        resultado = cnpj_utils.buscar_dados_cnpj(CNPJ_VALIDO)
        assert resultado["razao_social"] == "BB via minhareceita"

    def test_retorna_none_quando_as_duas_fontes_falham(self, monkeypatch):
        monkeypatch.setattr(cnpj_utils.requests, "get", MagicMock(return_value=_resposta_erro(404)))
        assert cnpj_utils.buscar_dados_cnpj(CNPJ_VALIDO) is None

    def test_resultado_com_sucesso_fica_em_cache(self, monkeypatch):
        mock_get = MagicMock(
            return_value=_resposta_ok({"razao_social": "BB", "descricao_situacao_cadastral": "ATIVA"})
        )
        monkeypatch.setattr(cnpj_utils.requests, "get", mock_get)

        primeira = cnpj_utils.buscar_dados_cnpj(CNPJ_VALIDO)
        segunda = cnpj_utils.buscar_dados_cnpj(CNPJ_VALIDO)
        assert primeira == segunda
        assert mock_get.call_count == 1  # a segunda chamada veio do cache, não bateu na rede

    def test_falha_nao_fica_em_cache_e_permite_nova_tentativa(self, monkeypatch):
        mock_get = MagicMock(return_value=_resposta_erro(404))
        monkeypatch.setattr(cnpj_utils.requests, "get", mock_get)

        assert cnpj_utils.buscar_dados_cnpj(CNPJ_VALIDO) is None
        assert cnpj_utils.buscar_dados_cnpj(CNPJ_VALIDO) is None
        # 2 fontes x 2 tentativas — nenhuma falha ficou em cache.
        assert mock_get.call_count == 4

    def test_rate_limiter_espaca_chamadas_consecutivas_pra_mesma_fonte(self, monkeypatch):
        monkeypatch.setattr(cnpj_utils, "INTERVALO_MINIMO_SEGUNDOS", 0.3)
        mock_get = MagicMock(
            return_value=_resposta_ok({"razao_social": "X", "descricao_situacao_cadastral": "ATIVA"})
        )
        monkeypatch.setattr(cnpj_utils.requests, "get", mock_get)

        cnpj_utils.buscar_dados_cnpj(CNPJ_VALIDO)  # 1a chamada à brasilapi, sem espera
        t0 = time.monotonic()
        cnpj_utils.buscar_dados_cnpj("33.000.167/0001-01")  # CNPJ diferente -> não usa cache
        duracao = time.monotonic() - t0

        assert duracao >= 0.3 * 0.9
