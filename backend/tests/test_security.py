"""Testa a configuração de CORS e os headers de segurança de resposta.

Sem CORS_ORIGINS definida (caso destes testes), só os origins de
desenvolvimento local devem ser aceitos — nunca "*".
"""


def test_resposta_inclui_headers_de_seguranca(client):
    resposta = client.get("/")
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert resposta.headers["x-frame-options"] == "DENY"
    assert resposta.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_cors_aceita_origin_de_desenvolvimento_conhecido(client):
    resposta = client.get("/", headers={"Origin": "http://localhost:5173"})
    assert resposta.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_nao_reflete_origin_desconhecida(client):
    resposta = client.get("/", headers={"Origin": "https://site-malicioso.example.com"})
    assert "access-control-allow-origin" not in resposta.headers
