"""Testes pra parte do coletor que grava o estado da rodada (usado por
GET /status/pncp) — não testa a coleta em si (bate na rede real do PNCP,
fora do escopo da suíte automatizada)."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

import collector_pncp
from app import models
from app.database import SessionLocal


def _ultimo_estado():
    db = SessionLocal()
    try:
        return db.query(models.EstadoColetor).order_by(models.EstadoColetor.id.desc()).first()
    finally:
        db.close()


def test_registrar_estado_coletor_grava_execucao_com_sucesso():
    collector_pncp._registrar_estado_coletor(
        sucesso=True,
        total_modalidades=5,
        modalidades_com_falha=0,
        total_coletado=42,
        mensagem="",
    )

    estado = _ultimo_estado()
    assert estado.sucesso is True
    assert estado.total_modalidades == 5
    assert estado.modalidades_com_falha == 0
    assert estado.total_coletado == 42


def test_registrar_estado_coletor_grava_execucao_com_falha():
    collector_pncp._registrar_estado_coletor(
        sucesso=False,
        total_modalidades=5,
        modalidades_com_falha=2,
        total_coletado=10,
        mensagem="modalidade=Pregão - Eletrônico, uf=SP: Falha persistente",
    )

    estado = _ultimo_estado()
    assert estado.sucesso is False
    assert estado.modalidades_com_falha == 2
    assert "Falha persistente" in estado.mensagem


def test_registrar_estado_coletor_trunca_mensagem_muito_longa():
    mensagem_gigante = "x" * 5000
    collector_pncp._registrar_estado_coletor(
        sucesso=False,
        total_modalidades=1,
        modalidades_com_falha=1,
        total_coletado=0,
        mensagem=mensagem_gigante,
    )

    estado = _ultimo_estado()
    assert len(estado.mensagem) <= 2000


def _contratacao_falsa(numero_controle: str) -> dict:
    return {
        "numeroControlePNCP": numero_controle,
        "orgaoEntidade": {"cnpj": "12345678000199", "razaosocial": "Órgão Teste"},
        "unidadeOrgao": {"municipioNome": "Cidade Teste", "ufSigla": "MA"},
        "objetoCompra": "objeto de teste",
        "anoCompra": 2026,
        "sequencialCompra": 1,
    }


def _contar_salvos(prefixo: str) -> int:
    db = SessionLocal()
    try:
        return db.query(models.Licitacao).filter(models.Licitacao.numero_controle.like(f"{prefixo}%")).count()
    finally:
        db.close()


def test_salvar_licitacoes_grava_em_varios_lotes_cada_um_com_conexao_propria(monkeypatch):
    """Bug real: uma conexão só, reaproveitada pra gravação inteira, caiu
    consistentemente no meio de uma gravação grande contra Postgres remoto
    ("SSL connection has been closed unexpectedly"). Cada lote agora abre
    sua própria conexão — verifica que _salvar_lote é chamado uma vez por
    lote, e que todos os registros são salvos independente de quantos
    lotes isso levou."""
    monkeypatch.setattr(collector_pncp, "TAMANHO_LOTE_COMMIT", 3)
    chamadas_salvar_lote = MagicMock(wraps=collector_pncp._salvar_lote)
    monkeypatch.setattr(collector_pncp, "_salvar_lote", chamadas_salvar_lote)

    contratacoes = {
        f"PNCP-lote-teste-{i}": _contratacao_falsa(f"PNCP-lote-teste-{i}") for i in range(7)
    }
    collector_pncp.salvar_licitacoes(contratacoes)

    # 7 registros, lote de 3 -> 3 lotes (3 + 3 + 1).
    assert chamadas_salvar_lote.call_count == 3
    assert _contar_salvos("PNCP-lote-teste-") == 7


def test_salvar_lote_com_retry_tenta_de_novo_apos_conexao_cair(monkeypatch):
    """Se um lote falhar por queda de conexão, tenta de novo com uma
    conexão nova — como a gravação é um upsert, refazer o lote é seguro."""
    chamadas = {"total": 0}
    lote_original = collector_pncp._salvar_lote

    def falha_na_primeira_depois_funciona(lote, agora):
        chamadas["total"] += 1
        if chamadas["total"] == 1:
            raise OperationalError("SELECT 1", {}, Exception("SSL connection has been closed unexpectedly"))
        lote_original(lote, agora)

    monkeypatch.setattr(collector_pncp, "_salvar_lote", falha_na_primeira_depois_funciona)
    monkeypatch.setattr(collector_pncp.time, "sleep", lambda segundos: None)

    contratacoes = [("PNCP-retry-teste-1", _contratacao_falsa("PNCP-retry-teste-1"))]
    collector_pncp._salvar_lote_com_retry(contratacoes, datetime.utcnow())

    assert chamadas["total"] == 2  # falhou uma vez, teve sucesso na segunda
    assert _contar_salvos("PNCP-retry-teste-") == 1


def test_salvar_lote_com_retry_desiste_apos_esgotar_tentativas(monkeypatch):
    def sempre_falha(lote, agora):
        raise OperationalError("SELECT 1", {}, Exception("conexão caiu"))

    monkeypatch.setattr(collector_pncp, "_salvar_lote", sempre_falha)
    monkeypatch.setattr(collector_pncp, "MAX_TENTATIVAS_LOTE", 2)
    monkeypatch.setattr(collector_pncp.time, "sleep", lambda segundos: None)

    with pytest.raises(RuntimeError, match="Falha persistente salvando lote"):
        collector_pncp._salvar_lote_com_retry([], datetime.utcnow())


def test_marcar_inativas_marca_licitacoes_que_sumiram_da_coleta():
    numero_controle = "PNCP-marcar-inativa-teste"
    collector_pncp.salvar_licitacoes({numero_controle: _contratacao_falsa(numero_controle)})

    marcadas = collector_pncp.marcar_inativas(set())  # nenhum id "visto" nessa rodada

    db = SessionLocal()
    try:
        lic = db.query(models.Licitacao).filter(models.Licitacao.numero_controle == numero_controle).first()
        assert lic.ativa is False
        assert marcadas >= 1
    finally:
        db.close()
