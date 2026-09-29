"""Testes de integração pra /equipe (empresa, sincronização de CNPJ, membros e convites)."""

from app import cnpj_utils


def test_minha_empresa_retorna_dados_da_empresa_do_usuario(client, usuario_autenticado):
    resposta = client.get("/equipe/empresa", headers=usuario_autenticado)
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Empresa Teste"


def test_owner_pode_atualizar_dados_da_empresa(client, usuario_autenticado):
    resposta = client.put(
        "/equipe/empresa",
        headers=usuario_autenticado,
        json={"cnpj": "11222333000181", "endereco_uf": "SP"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["cnpj"] == "11222333000181"
    assert corpo["endereco_uf"] == "SP"


def test_membro_comum_nao_pode_atualizar_empresa(client, usuario_autenticado, criar_membro):
    headers_membro = criar_membro(usuario_autenticado)
    resposta = client.put("/equipe/empresa", headers=headers_membro, json={"nome": "Nome hostil"})
    assert resposta.status_code == 403


def test_listar_membros_inclui_owner_e_convidados(client, usuario_autenticado, criar_membro):
    headers_membro = criar_membro(usuario_autenticado, email="colega@example.com")

    resposta = client.get("/equipe/membros", headers=usuario_autenticado)
    assert resposta.status_code == 200
    emails = {m["email"] for m in resposta.json()}
    assert "colega@example.com" in emails

    # O membro vê a mesma equipe (mesma empresa) que o owner.
    resposta_membro = client.get("/equipe/membros", headers=headers_membro)
    assert resposta_membro.status_code == 200
    assert {m["email"] for m in resposta_membro.json()} == emails


def test_owner_pode_convidar_membro(client, usuario_autenticado):
    resposta = client.post("/equipe/convidar", headers=usuario_autenticado, json={"email": "novo@example.com"})
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["email_convidado"] == "novo@example.com"
    assert corpo["usado"] is False
    assert corpo["token"]


def test_membro_comum_nao_pode_convidar(client, usuario_autenticado, criar_membro):
    headers_membro = criar_membro(usuario_autenticado)
    resposta = client.post("/equipe/convidar", headers=headers_membro, json={"email": "outro@example.com"})
    assert resposta.status_code == 403


def test_registrar_com_convite_entra_como_membro_na_empresa_existente(client, usuario_autenticado):
    resposta_empresa = client.get("/equipe/empresa", headers=usuario_autenticado)
    empresa_id_owner = resposta_empresa.json()["id"]

    resposta_convite = client.post(
        "/equipe/convidar", headers=usuario_autenticado, json={"email": "convidado@example.com"}
    )
    token_convite = resposta_convite.json()["token"]

    resposta_registro = client.post(
        "/auth/registrar",
        json={"email": "convidado@example.com", "senha": "senha-123456", "token_convite": token_convite},
    )
    assert resposta_registro.status_code == 201
    corpo = resposta_registro.json()
    assert corpo["papel"] == "membro"
    assert corpo["empresa_id"] == empresa_id_owner


def test_registrar_com_token_convite_invalido_e_rejeitado(client):
    resposta = client.post(
        "/auth/registrar",
        json={"email": "sem.convite@example.com", "senha": "senha-123456", "token_convite": "token-inexistente"},
    )
    assert resposta.status_code == 400


def test_sincronizar_cnpj_sem_cnpj_cadastrado_retorna_400(client, usuario_autenticado):
    resposta = client.post("/equipe/empresa/sincronizar-cnpj", headers=usuario_autenticado)
    assert resposta.status_code == 400


def test_sincronizar_cnpj_com_sucesso_preenche_campos_vazios(client, usuario_autenticado, monkeypatch):
    client.put("/equipe/empresa", headers=usuario_autenticado, json={"cnpj": "11222333000181"})

    monkeypatch.setattr(
        cnpj_utils,
        "buscar_dados_cnpj",
        lambda cnpj: {
            "razao_social": "Empresa Sincronizada LTDA",
            "situacao_cadastral": "ATIVA",
            "endereco_logradouro": "Rua Teste",
            "endereco_numero": "100",
            "endereco_complemento": "",
            "endereco_bairro": "Centro",
            "endereco_cidade": "São Luís",
            "endereco_uf": "MA",
            "endereco_cep": "65000-000",
        },
    )

    resposta = client.post("/equipe/empresa/sincronizar-cnpj", headers=usuario_autenticado)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["situacao_cadastral"] == "ATIVA"
    assert corpo["endereco_cidade"] == "São Luís"
    assert corpo["cnpj_sincronizado_em"] is not None
    # "Empresa Teste" já estava preenchido no cadastro — não deve ser sobrescrito.
    assert corpo["nome"] == "Empresa Teste"


def test_sincronizar_cnpj_quando_fontes_externas_falham_retorna_502(client, usuario_autenticado, monkeypatch):
    client.put("/equipe/empresa", headers=usuario_autenticado, json={"cnpj": "11222333000181"})
    monkeypatch.setattr(cnpj_utils, "buscar_dados_cnpj", lambda cnpj: None)

    resposta = client.post("/equipe/empresa/sincronizar-cnpj", headers=usuario_autenticado)
    assert resposta.status_code == 502


def test_equipe_endpoints_exigem_autenticacao(client):
    assert client.get("/equipe/empresa").status_code == 401
    assert client.get("/equipe/membros").status_code == 401
    assert client.post("/equipe/convidar", json={"email": "x@example.com"}).status_code == 401
