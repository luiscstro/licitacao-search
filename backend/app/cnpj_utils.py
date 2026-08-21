"""
Busca de dados cadastrais de CNPJ via APIs públicas construídas em cima
dos Dados Abertos do CNPJ (Receita Federal) — sem login, sem CAPTCHA.
Diferente da consulta oficial da Receita (que tem CAPTCHA), essa é uma
via alternativa real: BrasilAPI e MinhaReceita servem os mesmos dados
abertos que a Receita publica mensalmente.
"""

import re

import requests

TIMEOUT_SEGUNDOS = 8


def _normalizar_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj or "")


def _extrair_brasilapi(dados: dict) -> dict:
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


def _extrair_minhareceita(dados: dict) -> dict:
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


def buscar_dados_cnpj(cnpj: str) -> dict | None:
    """Retorna um dict com razao_social, situacao_cadastral e endereco_*,
    ou None se nenhuma das duas fontes respondeu. Tenta BrasilAPI primeiro,
    cai pra MinhaReceita se falhar."""
    cnpj_limpo = _normalizar_cnpj(cnpj)
    if len(cnpj_limpo) != 14:
        raise ValueError("CNPJ precisa ter 14 dígitos")

    try:
        resp = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}", timeout=TIMEOUT_SEGUNDOS)
        if resp.status_code == 200:
            return _extrair_brasilapi(resp.json())
    except requests.RequestException:
        pass

    try:
        resp = requests.get(f"https://minhareceita.org/{cnpj_limpo}", timeout=TIMEOUT_SEGUNDOS)
        if resp.status_code == 200:
            return _extrair_minhareceita(resp.json())
    except requests.RequestException:
        pass

    return None
