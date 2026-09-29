"""Testes de integração pra GET /status/pncp — avisa o usuário quando o
coletor do PNCP falhou ou está desatualizado."""

from datetime import datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal


@pytest.fixture(autouse=True)
def _limpar_estado_coletor():
    """EstadoColetor não é isolado por empresa/usuário (é estado global do
    coletor) — sem limpar entre testes, uma linha antiga de um teste
    contaminaria a consulta "mais recente" do próximo, já que o banco
    SQLite é compartilhado durante toda a sessão de teste."""
    db = SessionLocal()
    try:
        db.query(models.EstadoColetor).delete()
        db.commit()
    finally:
        db.close()
    yield


def _inserir_estado(**overrides):
    dados = {
        "sucesso": True,
        "total_modalidades": 5,
        "modalidades_com_falha": 0,
        "total_coletado": 100,
        "mensagem": "",
        "executado_em": datetime.utcnow(),
    }
    dados.update(overrides)
    db = SessionLocal()
    try:
        db.add(models.EstadoColetor(**dados))
        db.commit()
    finally:
        db.close()


def test_sem_nenhuma_execucao_registrada_nao_soa_alarme(client, usuario_autenticado):
    resposta = client.get("/status/pncp", headers=usuario_autenticado)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ultima_execucao_em"] is None
    assert corpo["pncp_instavel"] is False
    assert corpo["dados_desatualizados"] is False


def test_ultima_execucao_com_sucesso_e_recente_nao_soa_alarme(client, usuario_autenticado):
    _inserir_estado(sucesso=True, executado_em=datetime.utcnow() - timedelta(hours=2))

    resposta = client.get("/status/pncp", headers=usuario_autenticado)
    corpo = resposta.json()
    assert corpo["pncp_instavel"] is False
    assert corpo["dados_desatualizados"] is False
    assert corpo["ultima_execucao_com_sucesso"] is True


def test_ultima_execucao_falhou_marca_pncp_instavel(client, usuario_autenticado):
    _inserir_estado(
        sucesso=False,
        executado_em=datetime.utcnow() - timedelta(minutes=10),
        mensagem="modalidade=Pregão - Eletrônico: Falha persistente",
    )

    resposta = client.get("/status/pncp", headers=usuario_autenticado)
    corpo = resposta.json()
    assert corpo["pncp_instavel"] is True
    assert corpo["dados_desatualizados"] is True
    assert corpo["ultima_execucao_com_sucesso"] is False


def test_ultima_execucao_falhou_mas_ja_teve_sucesso_antes_preenche_data_do_ultimo_sucesso(
    client, usuario_autenticado
):
    _inserir_estado(sucesso=True, executado_em=datetime.utcnow() - timedelta(hours=25))
    _inserir_estado(sucesso=False, executado_em=datetime.utcnow() - timedelta(minutes=5))

    resposta = client.get("/status/pncp", headers=usuario_autenticado)
    corpo = resposta.json()
    assert corpo["pncp_instavel"] is True
    assert corpo["ultima_coleta_com_sucesso_em"] is not None
    assert corpo["horas_desde_ultima_coleta_com_sucesso"] > 24


def test_muito_tempo_sem_coleta_bem_sucedida_marca_dados_desatualizados_mesmo_sem_falha_registrada(
    client, usuario_autenticado
):
    _inserir_estado(sucesso=True, executado_em=datetime.utcnow() - timedelta(hours=40))

    resposta = client.get("/status/pncp", headers=usuario_autenticado)
    corpo = resposta.json()
    assert corpo["pncp_instavel"] is False  # a última execução registrada teve sucesso
    assert corpo["dados_desatualizados"] is True  # mas faz tempo demais desde então


def test_coleta_recente_com_sucesso_depois_de_uma_falha_antiga_nao_soa_alarme(client, usuario_autenticado):
    _inserir_estado(sucesso=False, executado_em=datetime.utcnow() - timedelta(hours=48))
    _inserir_estado(sucesso=True, executado_em=datetime.utcnow() - timedelta(hours=1))

    resposta = client.get("/status/pncp", headers=usuario_autenticado)
    corpo = resposta.json()
    assert corpo["pncp_instavel"] is False
    assert corpo["dados_desatualizados"] is False


def test_status_pncp_exige_autenticacao(client):
    resposta = client.get("/status/pncp")
    assert resposta.status_code == 401
