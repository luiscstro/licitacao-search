"""Testes de registro/login (app/main.py + app/auth.py)."""

from app import auth


def test_registrar_e_login_retorna_token(client):
    email = "novo.usuario@example.com"
    senha = "minha-senha-forte-1"

    resposta_registro = client.post(
        "/auth/registrar",
        json={"email": email, "senha": senha, "nome_empresa": "Minha Empresa"},
    )
    assert resposta_registro.status_code == 201
    corpo = resposta_registro.json()
    assert corpo["email"] == email
    assert corpo["papel"] == "owner"

    resposta_login = client.post(
        "/auth/login",
        data={"username": email, "password": senha},
    )
    assert resposta_login.status_code == 200
    token_dados = resposta_login.json()
    assert token_dados["token_type"] == "bearer"
    assert token_dados["access_token"]
    assert token_dados["refresh_token"]

    # Token deve funcionar em rota protegida.
    resposta_me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token_dados['access_token']}"},
    )
    assert resposta_me.status_code == 200
    assert resposta_me.json()["email"] == email


def test_login_com_senha_errada_e_rejeitado(client):
    email = "outro.usuario@example.com"
    senha_correta = "senha-correta-123"

    resposta_registro = client.post(
        "/auth/registrar",
        json={"email": email, "senha": senha_correta, "nome_empresa": "Empresa X"},
    )
    assert resposta_registro.status_code == 201

    resposta_login = client.post(
        "/auth/login",
        data={"username": email, "password": "senha-errada"},
    )
    assert resposta_login.status_code == 401


def test_registrar_email_duplicado_e_rejeitado(client):
    email = "duplicado@example.com"
    senha = "senha-qualquer-123"

    primeira = client.post(
        "/auth/registrar",
        json={"email": email, "senha": senha, "nome_empresa": "Empresa Y"},
    )
    assert primeira.status_code == 201

    segunda = client.post(
        "/auth/registrar",
        json={"email": email, "senha": senha, "nome_empresa": "Empresa Y de novo"},
    )
    assert segunda.status_code == 400


def _registrar_e_logar(client, email, senha="senha-123456"):
    resposta = client.post("/auth/registrar", json={"email": email, "senha": senha, "nome_empresa": "Empresa"})
    assert resposta.status_code == 201, resposta.text
    login = client.post("/auth/login", data={"username": email, "password": senha})
    assert login.status_code == 200, login.text
    return login.json()


def test_refresh_token_emite_novo_access_token_e_rotaciona_o_refresh(client):
    email = "refresh.rotacao@example.com"
    tokens = _registrar_e_logar(client, email)

    resposta = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resposta.status_code == 200
    novos_tokens = resposta.json()
    assert novos_tokens["access_token"]
    assert novos_tokens["refresh_token"]
    assert novos_tokens["refresh_token"] != tokens["refresh_token"]

    # O novo access token funciona numa rota protegida.
    resposta_me = client.get("/auth/me", headers={"Authorization": f"Bearer {novos_tokens['access_token']}"})
    assert resposta_me.status_code == 200
    assert resposta_me.json()["email"] == email


def test_refresh_token_usado_duas_vezes_e_rejeitado_na_segunda(client):
    tokens = _registrar_e_logar(client, "refresh.reuso@example.com")

    primeira = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert primeira.status_code == 200

    segunda = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert segunda.status_code == 401


def test_refresh_token_invalido_e_rejeitado(client):
    resposta = client.post("/auth/refresh", json={"refresh_token": "token-que-nao-existe"})
    assert resposta.status_code == 401


def test_logout_revoga_o_refresh_token(client):
    tokens = _registrar_e_logar(client, "logout@example.com")

    resposta_logout = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert resposta_logout.status_code == 204

    resposta_refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resposta_refresh.status_code == 401


def test_logout_com_token_ja_revogado_nao_da_erro(client):
    tokens = _registrar_e_logar(client, "logout.duplo@example.com")

    client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    resposta_de_novo = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert resposta_de_novo.status_code == 204


def test_login_bloqueia_apos_muitas_tentativas_falhas(client):
    email = "vitima.forca.bruta@example.com"
    senha_correta = "senha-correta-123"
    client.post("/auth/registrar", json={"email": email, "senha": senha_correta, "nome_empresa": "Empresa"})

    for _ in range(auth.MAX_TENTATIVAS_LOGIN):
        resposta = client.post("/auth/login", data={"username": email, "password": "senha-errada"})
        assert resposta.status_code == 401

    # A tentativa seguinte é bloqueada mesmo com a senha CERTA.
    bloqueada = client.post("/auth/login", data={"username": email, "password": senha_correta})
    assert bloqueada.status_code == 429


def test_login_bloqueado_nao_afeta_outra_conta(client):
    vitima = "outra.vitima@example.com"
    senha_vitima = "senha-vitima-123"
    client.post("/auth/registrar", json={"email": vitima, "senha": senha_vitima, "nome_empresa": "Empresa"})
    for _ in range(auth.MAX_TENTATIVAS_LOGIN):
        client.post("/auth/login", data={"username": vitima, "password": "senha-errada"})

    outro_email = "conta.nao.afetada@example.com"
    senha_outro = "senha-outro-123"
    client.post("/auth/registrar", json={"email": outro_email, "senha": senha_outro, "nome_empresa": "Empresa"})
    resposta = client.post("/auth/login", data={"username": outro_email, "password": senha_outro})
    assert resposta.status_code == 200


def test_login_com_sucesso_zera_o_contador_de_tentativas(client):
    email = "reseta.contador@example.com"
    senha = "senha-correta-123"
    client.post("/auth/registrar", json={"email": email, "senha": senha, "nome_empresa": "Empresa"})

    for _ in range(auth.MAX_TENTATIVAS_LOGIN - 1):
        client.post("/auth/login", data={"username": email, "password": "senha-errada"})

    sucesso = client.post("/auth/login", data={"username": email, "password": senha})
    assert sucesso.status_code == 200

    # O login certo zerou o contador — não deve estar bloqueado.
    de_novo = client.post("/auth/login", data={"username": email, "password": senha})
    assert de_novo.status_code == 200


def test_access_token_expira_em_ate_uma_hora():
    from datetime import datetime

    from jose import jwt

    token = auth.criar_token({"sub": "alguem@example.com"})
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    expira_em = datetime.utcfromtimestamp(payload["exp"])
    duracao_minutos = (expira_em - datetime.utcnow()).total_seconds() / 60
    assert 0 < duracao_minutos <= 60
