"""Testes de integração pra /comentarios."""


def test_criar_e_listar_comentario(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()

    resposta_criar = client.post(
        "/comentarios",
        headers=usuario_autenticado,
        json={"numero_controle": numero_controle, "texto": "Vamos participar dessa."},
    )
    assert resposta_criar.status_code == 201
    corpo = resposta_criar.json()
    assert corpo["texto"] == "Vamos participar dessa."
    assert corpo["autor_email"]

    resposta_lista = client.get(
        "/comentarios", headers=usuario_autenticado, params={"numero_controle": numero_controle}
    )
    assert resposta_lista.status_code == 200
    itens = resposta_lista.json()
    assert len(itens) == 1
    assert itens[0]["texto"] == "Vamos participar dessa."


def test_criar_comentario_em_licitacao_inexistente_retorna_404(client, usuario_autenticado):
    resposta = client.post(
        "/comentarios",
        headers=usuario_autenticado,
        json={"numero_controle": "PNCP-nao-existe", "texto": "Comentário órfão"},
    )
    assert resposta.status_code == 404


def test_comentarios_sao_listados_do_mais_recente_para_o_mais_antigo(
    client, usuario_autenticado, criar_licitacao
):
    numero_controle = criar_licitacao()
    client.post(
        "/comentarios", headers=usuario_autenticado, json={"numero_controle": numero_controle, "texto": "Primeiro"}
    )
    client.post(
        "/comentarios", headers=usuario_autenticado, json={"numero_controle": numero_controle, "texto": "Segundo"}
    )

    resposta = client.get(
        "/comentarios", headers=usuario_autenticado, params={"numero_controle": numero_controle}
    )
    textos = [c["texto"] for c in resposta.json()]
    assert textos == ["Segundo", "Primeiro"]


def test_comentarios_sao_visiveis_para_toda_a_equipe(client, usuario_autenticado, criar_membro, criar_licitacao):
    headers_membro = criar_membro(usuario_autenticado)
    numero_controle = criar_licitacao()

    client.post(
        "/comentarios", headers=usuario_autenticado, json={"numero_controle": numero_controle, "texto": "Do owner"}
    )

    resposta_membro = client.get(
        "/comentarios", headers=headers_membro, params={"numero_controle": numero_controle}
    )
    assert resposta_membro.status_code == 200
    assert [c["texto"] for c in resposta_membro.json()] == ["Do owner"]


def test_comentarios_exigem_autenticacao(client):
    assert client.get("/comentarios", params={"numero_controle": "x"}).status_code == 401
    assert (
        client.post("/comentarios", json={"numero_controle": "x", "texto": "y"}).status_code == 401
    )
