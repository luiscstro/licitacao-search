"""Testes pra parte do coletor que grava o estado da rodada (usado por
GET /status/pncp) — não testa a coleta em si (bate na rede real do PNCP,
fora do escopo da suíte automatizada)."""

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
