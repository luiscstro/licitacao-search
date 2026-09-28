"""
Configuração compartilhada dos testes.

IMPORTANTE: `DATABASE_URL` e `SECRET_KEY` precisam ser definidas ANTES de
importar `app.main` — a criação das tabelas (`Base.metadata.create_all`) e a
resolução da chave secreta acontecem no import do módulo, não em tempo de
execução de cada teste. Por isso isso tudo roda no topo do conftest, antes
de qualquer `import app...`.
"""

import os
import tempfile
import uuid

import pytest

# Banco de dados SQLite temporário, isolado por sessão de teste — nunca toca
# no licitacoes_saas.db real usado em desenvolvimento.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["SECRET_KEY"] = "chave-fixa-de-teste-nao-usar-em-producao"

from app import main  # noqa: E402 (import precisa vir depois de setar as env vars acima)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_db_file():
    yield
    try:
        os.remove(_db_path)
    except OSError:
        pass


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def usuario_autenticado(client):
    """Registra um usuário novo (empresa própria) e devolve headers de autenticação.

    O e-mail é único por chamada (mesmo banco SQLite persiste durante toda a
    sessão de teste), pra testes diferentes não colidirem entre si."""
    email = f"teste.{uuid.uuid4().hex[:12]}@example.com"
    senha = "senha-super-segura-123"
    resposta = client.post(
        "/auth/registrar",
        json={"email": email, "senha": senha, "nome_empresa": "Empresa Teste"},
    )
    assert resposta.status_code == 201, resposta.text

    login = client.post(
        "/auth/login",
        data={"username": email, "password": senha},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers


@pytest.fixture
def criar_licitacao():
    """Insere uma licitação direto no banco (contorna o coletor real) e
    devolve o numero_controle gerado. Usado por testes de favoritos,
    pipeline, comentários e documentos, que dependem de uma licitação
    existente para referenciar via numero_controle."""
    from app import models
    from app.database import SessionLocal

    def _criar(**overrides):
        dados = {
            "numero_controle": f"PNCP-teste-{uuid.uuid4().hex[:12]}",
            "orgao": "Órgão Teste",
            "cidade": "Cidade Teste",
            "uf": "MA",
            "objeto": "objeto de teste",
            "valor_estimado": 1000,
            "modalidade": "Pregão Eletrônico",
            "texto_busca": "objeto de teste orgao teste cidade teste",
            "texto_busca_objeto": "objeto de teste",
            "ativa": True,
        }
        dados.update(overrides)
        db = SessionLocal()
        try:
            db.add(models.Licitacao(**dados))
            db.commit()
        finally:
            db.close()
        return dados["numero_controle"]

    return _criar


@pytest.fixture
def criar_membro(client):
    """Convida (como owner) e registra um segundo usuário na mesma empresa
    do owner informado, devolvendo os headers de autenticação do membro."""

    def _criar(headers_owner, email=None):
        email = email or f"membro.{uuid.uuid4().hex[:12]}@example.com"
        senha = "senha-do-membro-123"

        resposta_convite = client.post("/equipe/convidar", headers=headers_owner, json={"email": email})
        assert resposta_convite.status_code == 201, resposta_convite.text
        token_convite = resposta_convite.json()["token"]

        resposta_registro = client.post(
            "/auth/registrar",
            json={"email": email, "senha": senha, "token_convite": token_convite},
        )
        assert resposta_registro.status_code == 201, resposta_registro.text

        login = client.post("/auth/login", data={"username": email, "password": senha})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _criar
