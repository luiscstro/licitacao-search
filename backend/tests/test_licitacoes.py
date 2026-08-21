"""Testes de integração pra busca de licitações — foco nos filtros de UASG
e número do pregão (`codigo_unidade`/`numero_compra`)."""

from app import models
from app.database import SessionLocal


def _inserir_licitacao(**overrides):
    dados = {
        "numero_controle": "PNCP-00000000000000-1-000001/2026",
        "orgao": "Órgão Teste",
        "cidade": "Cidade Teste",
        "uf": "MA",
        "objeto": "objeto de teste",
        "valor_estimado": 1000,
        "modalidade": "Pregão Eletrônico",
        "texto_busca": "objeto de teste orgao teste cidade teste",
        "texto_busca_objeto": "objeto de teste",
        "codigo_unidade": None,
        "numero_compra": None,
        "ativa": True,
    }
    dados.update(overrides)
    db = SessionLocal()
    try:
        db.add(models.Licitacao(**dados))
        db.commit()
    finally:
        db.close()


def test_busca_por_uasg(client, usuario_autenticado):
    _inserir_licitacao(numero_controle="PNCP-1-1-000001/2026", codigo_unidade="925326")
    _inserir_licitacao(numero_controle="PNCP-1-1-000002/2026", codigo_unidade="111222")

    resposta = client.get("/licitacoes", params={"uasg": "925326"}, headers=usuario_autenticado)
    assert resposta.status_code == 200
    itens = resposta.json()["itens"]
    assert len(itens) == 1
    assert itens[0]["codigo_unidade"] == "925326"


def test_busca_por_numero_pregao(client, usuario_autenticado):
    _inserir_licitacao(numero_controle="PNCP-2-1-000001/2026", numero_compra="90001/2025")
    _inserir_licitacao(numero_controle="PNCP-2-1-000002/2026", numero_compra="12345/2025")

    resposta = client.get("/licitacoes", params={"numero_pregao": "90001"}, headers=usuario_autenticado)
    assert resposta.status_code == 200
    itens = resposta.json()["itens"]
    assert len(itens) == 1
    assert itens[0]["numero_compra"] == "90001/2025"


def test_busca_livre_nao_exclui_licitacoes_sem_uasg_ou_pregao(client, usuario_autenticado):
    """Licitação sem codigo_unidade/numero_compra (comum: coletada antes da
    migração que adicionou essas colunas) continua aparecendo em buscas que
    não filtram por esses campos."""
    _inserir_licitacao(numero_controle="PNCP-3-1-000001/2026")

    resposta = client.get("/licitacoes", params={"busca": "objeto de teste"}, headers=usuario_autenticado)
    assert resposta.status_code == 200
    numeros = [i["numero_controle"] for i in resposta.json()["itens"]]
    assert "PNCP-3-1-000001/2026" in numeros
