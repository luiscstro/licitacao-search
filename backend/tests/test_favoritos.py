"""Testes de integração pra /favoritos."""


def test_favoritar_e_listar(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()

    resposta_favoritar = client.post(
        "/favoritos", headers=usuario_autenticado, json={"numero_controle": numero_controle}
    )
    assert resposta_favoritar.status_code == 201
    assert resposta_favoritar.json() == {"ok": True}

    resposta_lista = client.get("/favoritos", headers=usuario_autenticado)
    assert resposta_lista.status_code == 200
    itens = resposta_lista.json()
    assert len(itens) == 1
    assert itens[0]["numero_controle"] == numero_controle
    assert itens[0]["favoritada"] is True


def test_favoritar_licitacao_inexistente_retorna_404(client, usuario_autenticado):
    resposta = client.post(
        "/favoritos", headers=usuario_autenticado, json={"numero_controle": "PNCP-nao-existe"}
    )
    assert resposta.status_code == 404


def test_favoritar_a_mesma_licitacao_duas_vezes_e_idempotente(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()

    primeira = client.post(
        "/favoritos", headers=usuario_autenticado, json={"numero_controle": numero_controle}
    )
    assert primeira.status_code == 201
    assert primeira.json() == {"ok": True}

    segunda = client.post(
        "/favoritos", headers=usuario_autenticado, json={"numero_controle": numero_controle}
    )
    assert segunda.status_code == 201
    assert segunda.json() == {"ok": True, "ja_era_favorito": True}

    resposta_lista = client.get("/favoritos", headers=usuario_autenticado)
    assert len(resposta_lista.json()) == 1


def test_desfavoritar_remove_da_lista(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()
    client.post("/favoritos", headers=usuario_autenticado, json={"numero_controle": numero_controle})

    resposta_deletar = client.delete(
        "/favoritos", headers=usuario_autenticado, params={"numero_controle": numero_controle}
    )
    assert resposta_deletar.status_code == 204

    resposta_lista = client.get("/favoritos", headers=usuario_autenticado)
    assert resposta_lista.json() == []


def test_desfavoritar_algo_que_nunca_foi_favorito_nao_da_erro(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()
    resposta = client.delete(
        "/favoritos", headers=usuario_autenticado, params={"numero_controle": numero_controle}
    )
    assert resposta.status_code == 204


def test_favoritar_coloca_a_licitacao_no_pipeline_da_empresa(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()
    client.post("/favoritos", headers=usuario_autenticado, json={"numero_controle": numero_controle})

    resposta_pipeline = client.get("/pipeline", headers=usuario_autenticado)
    assert resposta_pipeline.status_code == 200
    numeros = [o["numero_controle"] for o in resposta_pipeline.json()]
    assert numero_controle in numeros


def test_desfavoritar_nao_remove_do_pipeline(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()
    client.post("/favoritos", headers=usuario_autenticado, json={"numero_controle": numero_controle})
    client.delete("/favoritos", headers=usuario_autenticado, params={"numero_controle": numero_controle})

    resposta_pipeline = client.get("/pipeline", headers=usuario_autenticado)
    numeros = [o["numero_controle"] for o in resposta_pipeline.json()]
    assert numero_controle in numeros


def test_favoritos_exigem_autenticacao(client):
    assert client.get("/favoritos").status_code == 401
    assert client.post("/favoritos", json={"numero_controle": "x"}).status_code == 401
    assert client.delete("/favoritos", params={"numero_controle": "x"}).status_code == 401
