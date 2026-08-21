"""Testes de integração pra CRUD de /criterios (autenticado)."""


def test_criar_listar_atualizar_deletar_criterio(client, usuario_autenticado):
    headers = usuario_autenticado

    # Lista vazia no começo.
    resposta_lista_inicial = client.get("/criterios", headers=headers)
    assert resposta_lista_inicial.status_code == 200
    assert resposta_lista_inicial.json() == []

    # Criar.
    resposta_criar = client.post(
        "/criterios",
        headers=headers,
        json={
            "nome": "TI - apoio administrativo",
            "palavra_obrigatoria": "apoio administrativo",
            "palavras_bonus": "informatica",
            "valor_minimo": 10000,
            "valor_maximo": 500000,
            "estados_permitidos": "SP,RJ",
            "exigir_dedicacao_exclusiva": False,
            "modalidades_permitidas": "",
        },
    )
    assert resposta_criar.status_code == 201, resposta_criar.text
    criterio_criado = resposta_criar.json()
    assert criterio_criado["nome"] == "TI - apoio administrativo"
    assert criterio_criado["ativo"] is True
    criterio_id = criterio_criado["id"]

    # Listar — deve conter o critério recém-criado.
    resposta_lista = client.get("/criterios", headers=headers)
    assert resposta_lista.status_code == 200
    ids = [c["id"] for c in resposta_lista.json()]
    assert criterio_id in ids

    # Atualizar.
    resposta_atualizar = client.put(
        f"/criterios/{criterio_id}",
        headers=headers,
        json={"nome": "Nome atualizado", "ativo": False},
    )
    assert resposta_atualizar.status_code == 200
    criterio_atualizado = resposta_atualizar.json()
    assert criterio_atualizado["nome"] == "Nome atualizado"
    assert criterio_atualizado["ativo"] is False

    # Deletar.
    resposta_deletar = client.delete(f"/criterios/{criterio_id}", headers=headers)
    assert resposta_deletar.status_code == 204

    resposta_lista_final = client.get("/criterios", headers=headers)
    ids_finais = [c["id"] for c in resposta_lista_final.json()]
    assert criterio_id not in ids_finais


def test_atualizar_criterio_inexistente_retorna_404(client, usuario_autenticado):
    headers = usuario_autenticado
    resposta = client.put(
        "/criterios/999999",
        headers=headers,
        json={"nome": "Não existe"},
    )
    assert resposta.status_code == 404


def test_criterios_exigem_autenticacao(client):
    resposta = client.get("/criterios")
    assert resposta.status_code == 401
