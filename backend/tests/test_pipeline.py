"""Testes de integração pra /pipeline (mini-CRM, compartilhado pela empresa)."""


def test_pipeline_vazio_inicialmente(client, usuario_autenticado):
    resposta = client.get("/pipeline", headers=usuario_autenticado)
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_atualizar_status_sem_estar_no_pipeline_retorna_404(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()
    resposta = client.put(
        "/pipeline",
        headers=usuario_autenticado,
        params={"numero_controle": numero_controle},
        json={"status": "analisando"},
    )
    assert resposta.status_code == 404


def test_atualizar_status_invalido_retorna_400(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()
    client.post("/favoritos", headers=usuario_autenticado, json={"numero_controle": numero_controle})

    resposta = client.put(
        "/pipeline",
        headers=usuario_autenticado,
        params={"numero_controle": numero_controle},
        json={"status": "status-que-nao-existe"},
    )
    assert resposta.status_code == 400


def test_atualizar_status_com_sucesso(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()
    client.post("/favoritos", headers=usuario_autenticado, json={"numero_controle": numero_controle})

    resposta = client.put(
        "/pipeline",
        headers=usuario_autenticado,
        params={"numero_controle": numero_controle},
        json={"status": "proposta_enviada"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "proposta_enviada"
    assert corpo["atualizado_por_email"]


def test_remover_do_pipeline(client, usuario_autenticado, criar_licitacao):
    numero_controle = criar_licitacao()
    client.post("/favoritos", headers=usuario_autenticado, json={"numero_controle": numero_controle})

    resposta_remover = client.delete(
        "/pipeline", headers=usuario_autenticado, params={"numero_controle": numero_controle}
    )
    assert resposta_remover.status_code == 204

    resposta_lista = client.get("/pipeline", headers=usuario_autenticado)
    numeros = [o["numero_controle"] for o in resposta_lista.json()]
    assert numero_controle not in numeros


def test_pipeline_e_compartilhado_entre_membros_da_mesma_empresa(
    client, usuario_autenticado, criar_membro, criar_licitacao
):
    headers_membro = criar_membro(usuario_autenticado)
    numero_controle = criar_licitacao()

    # Membro favorita -> aparece no pipeline visto pelo owner.
    client.post("/favoritos", headers=headers_membro, json={"numero_controle": numero_controle})
    resposta_owner = client.get("/pipeline", headers=usuario_autenticado)
    assert numero_controle in [o["numero_controle"] for o in resposta_owner.json()]

    # Owner consegue atualizar o status de uma oportunidade criada pelo membro.
    resposta_status = client.put(
        "/pipeline",
        headers=usuario_autenticado,
        params={"numero_controle": numero_controle},
        json={"status": "ganhou"},
    )
    assert resposta_status.status_code == 200
    assert resposta_status.json()["status"] == "ganhou"


def test_pipeline_exige_autenticacao(client):
    assert client.get("/pipeline").status_code == 401
    assert client.put("/pipeline", params={"numero_controle": "x"}, json={"status": "ganhou"}).status_code == 401
    assert client.delete("/pipeline", params={"numero_controle": "x"}).status_code == 401
