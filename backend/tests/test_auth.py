"""Testes de registro/login (app/main.py + app/auth.py)."""


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
