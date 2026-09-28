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


def _contratacao_falsa(numero_controle: str) -> dict:
    return {
        "numeroControlePNCP": numero_controle,
        "orgaoEntidade": {"cnpj": "12345678000199", "razaosocial": "Órgão Teste"},
        "unidadeOrgao": {"municipioNome": "Cidade Teste", "ufSigla": "MA"},
        "objetoCompra": "objeto de teste",
        "anoCompra": 2026,
        "sequencialCompra": 1,
    }


def test_salvar_licitacoes_comita_em_lotes_nao_so_no_final(monkeypatch):
    """Bug real: um commit só no final perdia a modalidade inteira se a
    conexão caísse no meio de uma gravação grande (aconteceu com Postgres
    remoto). Commitando em lotes, uma queda no meio perde só o lote atual."""
    monkeypatch.setattr(collector_pncp, "TAMANHO_LOTE_COMMIT", 3)

    db = SessionLocal()
    try:
        contador_commits = {"chamadas": 0}
        commit_original = db.commit

        def commit_contado():
            contador_commits["chamadas"] += 1
            commit_original()

        monkeypatch.setattr(db, "commit", commit_contado)

        contratacoes = {
            f"PNCP-lote-teste-{i}": _contratacao_falsa(f"PNCP-lote-teste-{i}") for i in range(7)
        }
        collector_pncp.salvar_licitacoes(db, contratacoes)

        # 7 registros, lote de 3 -> commits nos índices 3 e 6, mais o commit
        # final (índice 7, que não é múltiplo de 3) = 3 commits no total.
        assert contador_commits["chamadas"] == 3

        salvos = (
            db.query(models.Licitacao)
            .filter(models.Licitacao.numero_controle.like("PNCP-lote-teste-%"))
            .count()
        )
        assert salvos == 7
    finally:
        db.close()
