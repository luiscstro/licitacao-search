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
