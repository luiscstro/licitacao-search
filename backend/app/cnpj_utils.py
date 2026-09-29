"""
Busca de dados cadastrais de CNPJ via APIs públicas construídas em cima
dos Dados Abertos do CNPJ (Receita Federal) — sem login, sem CAPTCHA.
Diferente da consulta oficial da Receita (que tem CAPTCHA), essa é uma
via alternativa real: BrasilAPI e MinhaReceita servem os mesmos dados
abertos que a Receita publica mensalmente.

Duas proteções em cima das chamadas HTTP, já que são APIs públicas
gratuitas com limite de uso:
- Cache em memória por CNPJ (só de resultados com sucesso, TTL de 24h —
  dado cadastral muda raramente, não faz sentido bater na API de novo
  toda vez que a mesma empresa sincroniza).
- Intervalo mínimo entre requisições consecutivas pra cada fonte, pra
  não estourar o rate limit delas (o que bloquearia a sincronização de
  CNPJ pra todo mundo, não só pra quem disparou as requisições).
"""

import re
import threading
import time

import requests

TIMEOUT_SEGUNDOS = 8
CACHE_TTL_SEGUNDOS = 24 * 60 * 60  # 24h
INTERVALO_MINIMO_SEGUNDOS = 1.0  # no máx. 1 requisição/segundo por fonte

_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = threading.Lock()

_ultima_chamada: dict[str, float] = {"brasilapi": 0.0, "minhareceita": 0.0}
_limitador_lock = threading.Lock()


def _normalizar_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj or "")


def _digito_verificador(base: str) -> str:
    """Calcula um dígito verificador de CNPJ (módulo 11). Os pesos partem de
    2 pro dígito mais à direita e sobem até 9, voltando a 2 (ciclo de 8)."""
    pesos = []
    peso = 2
    for _ in range(len(base)):
        pesos.insert(0, peso)
        peso = peso + 1 if peso < 9 else 2

    soma = sum(int(digito) * p for digito, p in zip(base, pesos))
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def _cnpj_valido(cnpj_limpo: str) -> bool:
    """Valida tamanho e os dois dígitos verificadores — não só o formato.
    Sequências de dígito repetido (ex: "00000000000000") são inválidas mesmo
    quando passariam no cálculo do módulo 11 (caso conhecido do algoritmo)."""
    if len(cnpj_limpo) != 14 or len(set(cnpj_limpo)) == 1:
        return False

    primeiro_digito = _digito_verificador(cnpj_limpo[:12])
    segundo_digito = _digito_verificador(cnpj_limpo[:12] + primeiro_digito)
    return cnpj_limpo[12:] == primeiro_digito + segundo_digito


def _extrair_dados(dados: dict) -> dict:
    """BrasilAPI e MinhaReceita servem o mesmo dataset (Dados Abertos do
    CNPJ) e usam exatamente os mesmos nomes de campo — uma única extração
    serve pras duas fontes."""
    endereco = {
        "endereco_logradouro": dados.get("logradouro") or "",
        "endereco_numero": dados.get("numero") or "",
        "endereco_complemento": dados.get("complemento") or "",
        "endereco_bairro": dados.get("bairro") or "",
        "endereco_cidade": dados.get("municipio") or "",
        "endereco_uf": dados.get("uf") or "",
        "endereco_cep": dados.get("cep") or "",
    }
    return {
        "razao_social": dados.get("razao_social") or "",
        "situacao_cadastral": dados.get("descricao_situacao_cadastral") or "",
        **endereco,
    }


def _aguardar_limite(fonte: str) -> None:
    """Bloqueia até que passe INTERVALO_MINIMO_SEGUNDOS desde a última
    requisição feita pra essa fonte, pra respeitar o rate limit dela."""
    with _limitador_lock:
        agora = time.monotonic()
        espera = INTERVALO_MINIMO_SEGUNDOS - (agora - _ultima_chamada[fonte])
        if espera > 0:
            time.sleep(espera)
        _ultima_chamada[fonte] = time.monotonic()


def _consultar_fontes(cnpj_limpo: str) -> dict | None:
    _aguardar_limite("brasilapi")
    try:
        resp = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}", timeout=TIMEOUT_SEGUNDOS)
        if resp.status_code == 200:
            return _extrair_dados(resp.json())
    except requests.RequestException:
        pass

    _aguardar_limite("minhareceita")
    try:
        resp = requests.get(f"https://minhareceita.org/{cnpj_limpo}", timeout=TIMEOUT_SEGUNDOS)
        if resp.status_code == 200:
            return _extrair_dados(resp.json())
    except requests.RequestException:
        pass

    return None


def buscar_dados_cnpj(cnpj: str) -> dict | None:
    """Retorna um dict com razao_social, situacao_cadastral e endereco_*,
    ou None se nenhuma das duas fontes respondeu (CNPJ inexistente ou
    ambas fora do ar). Tenta BrasilAPI primeiro, cai pra MinhaReceita se
    falhar. Resultados com sucesso ficam em cache por CACHE_TTL_SEGUNDOS;
    falhas não ficam em cache, pra permitir nova tentativa manual."""
    cnpj_limpo = _normalizar_cnpj(cnpj)
    if not _cnpj_valido(cnpj_limpo):
        raise ValueError("CNPJ inválido")

    with _cache_lock:
        em_cache = _cache.get(cnpj_limpo)
    if em_cache is not None:
        gravado_em, resultado = em_cache
        if (time.monotonic() - gravado_em) < CACHE_TTL_SEGUNDOS:
            return resultado

    resultado = _consultar_fontes(cnpj_limpo)

    if resultado is not None:
        with _cache_lock:
            _cache[cnpj_limpo] = (time.monotonic(), resultado)
    return resultado
