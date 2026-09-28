"""Testes pra /admin/coletar-pncp — dispara o coletor remotamente pra
ambientes sem acesso a Shell (ex: plano free do Render). O subprocess real
(collector_pncp.py) é sempre mockado — esses testes não coletam nada de
verdade."""

import threading
import time
from unittest.mock import MagicMock

import pytest

from app import main


@pytest.fixture(autouse=True)
def _resetar_estado_coleta():
    """ADMIN_TOKEN é lido de os.getenv no import do módulo (mesmo padrão de
    SECRET_KEY em auth.py) — pra testar com/sem token configurado, cada
    teste ajusta `main.ADMIN_TOKEN` diretamente via monkeypatch, não a
    variável de ambiente (que não teria efeito depois do import)."""
    main._coleta_pncp_em_andamento = False
    yield
    main._coleta_pncp_em_andamento = False


def test_disparar_coleta_sem_admin_token_configurado_retorna_503(client, monkeypatch):
    monkeypatch.setattr(main, "ADMIN_TOKEN", None)
    resposta = client.post("/admin/coletar-pncp", headers={"x-admin-token": "qualquer-coisa"})
    assert resposta.status_code == 503


def test_disparar_coleta_com_token_errado_retorna_401(client, monkeypatch):
    monkeypatch.setattr(main, "ADMIN_TOKEN", "token-correto")
    resposta = client.post("/admin/coletar-pncp", headers={"x-admin-token": "token-errado"})
    assert resposta.status_code == 401


def test_disparar_coleta_sem_header_retorna_401(client, monkeypatch):
    monkeypatch.setattr(main, "ADMIN_TOKEN", "token-correto")
    resposta = client.post("/admin/coletar-pncp")
    assert resposta.status_code == 401


def test_disparar_coleta_com_token_certo_inicia_em_background(client, monkeypatch):
    monkeypatch.setattr(main, "ADMIN_TOKEN", "token-correto")
    mock_run = MagicMock(return_value=None)
    monkeypatch.setattr(main.subprocess, "run", mock_run)

    resposta = client.post("/admin/coletar-pncp", headers={"x-admin-token": "token-correto"})
    assert resposta.status_code == 202
    assert resposta.json()["status"] == "iniciado"

    # A thread roda em background — espera até o mock ser chamado (evita
    # sleep arbitrário / flakiness).
    for _ in range(50):
        if mock_run.called:
            break
        time.sleep(0.05)
    assert mock_run.called
    comando = mock_run.call_args.args[0]
    assert comando[-1] == "collector_pncp.py"


def test_disparar_coleta_duas_vezes_seguidas_retorna_409_na_segunda(client, monkeypatch):
    monkeypatch.setattr(main, "ADMIN_TOKEN", "token-correto")

    liberar = threading.Event()

    def _run_lento(*args, **kwargs):
        liberar.wait(timeout=5)

    monkeypatch.setattr(main.subprocess, "run", _run_lento)

    headers = {"x-admin-token": "token-correto"}
    primeira = client.post("/admin/coletar-pncp", headers=headers)
    assert primeira.status_code == 202

    segunda = client.post("/admin/coletar-pncp", headers=headers)
    assert segunda.status_code == 409

    liberar.set()  # libera a "coleta" presa pra não vazar pro próximo teste


def test_status_coleta_reflete_em_andamento(client, monkeypatch):
    monkeypatch.setattr(main, "ADMIN_TOKEN", "token-correto")
    headers = {"x-admin-token": "token-correto"}

    resposta_inicial = client.get("/admin/coletar-pncp/status", headers=headers)
    assert resposta_inicial.json() == {"em_andamento": False}

    liberar = threading.Event()

    def _run_lento(*args, **kwargs):
        liberar.wait(timeout=5)

    monkeypatch.setattr(main.subprocess, "run", _run_lento)
    client.post("/admin/coletar-pncp", headers=headers)

    resposta_durante = client.get("/admin/coletar-pncp/status", headers=headers)
    assert resposta_durante.json() == {"em_andamento": True}

    liberar.set()
    for _ in range(50):
        if not main._coleta_pncp_em_andamento:
            break
        time.sleep(0.05)

    resposta_final = client.get("/admin/coletar-pncp/status", headers=headers)
    assert resposta_final.json() == {"em_andamento": False}


def test_status_coleta_exige_admin_token(client, monkeypatch):
    monkeypatch.setattr(main, "ADMIN_TOKEN", "token-correto")
    resposta = client.get("/admin/coletar-pncp/status")
    assert resposta.status_code == 401
