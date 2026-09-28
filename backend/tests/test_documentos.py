"""Testes de integração pra /documentos (upload, atualização, substituição,
histórico, indicadores e remoção).

Os arquivos enviados durante os testes são gravados num diretório temporário
(`tmp_path`, via a fixture `_upload_dir_isolado` abaixo) — nunca no
`backend/uploads/` real usado em desenvolvimento.
"""

import pytest

from app import main


@pytest.fixture(autouse=True)
def _upload_dir_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)


def _arquivo_pdf(nome="certidao.pdf"):
    return {"file": (nome, b"%PDF-1.4 conteudo fake de teste", "application/pdf")}


def test_criar_e_listar_documento(client, usuario_autenticado):
    resposta = client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf(),
        data={"categoria": "fiscal", "nome": "Certidão Negativa Federal"},
    )
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["categoria"] == "fiscal"
    assert corpo["nome"] == "Certidão Negativa Federal"
    assert corpo["nome_arquivo_original"] == "certidao.pdf"
    assert corpo["status"] == "sem_data"
    assert corpo["enviado_por_email"]

    resposta_lista = client.get("/documentos", headers=usuario_autenticado)
    assert resposta_lista.status_code == 200
    assert len(resposta_lista.json()) == 1


def test_criar_documento_categoria_invalida_retorna_400(client, usuario_autenticado):
    resposta = client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf(),
        data={"categoria": "categoria-invalida", "nome": "Doc qualquer"},
    )
    assert resposta.status_code == 400


def test_criar_documento_extensao_nao_permitida_retorna_400(client, usuario_autenticado):
    resposta = client.post(
        "/documentos",
        headers=usuario_autenticado,
        files={"file": ("virus.exe", b"conteudo", "application/octet-stream")},
        data={"categoria": "fiscal", "nome": "Doc suspeito"},
    )
    assert resposta.status_code == 400


def test_listar_documentos_filtra_por_categoria(client, usuario_autenticado):
    client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf("fiscal.pdf"),
        data={"categoria": "fiscal", "nome": "Doc fiscal"},
    )
    client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf("juridico.pdf"),
        data={"categoria": "juridica", "nome": "Doc jurídico"},
    )

    resposta = client.get("/documentos", headers=usuario_autenticado, params={"categoria": "fiscal"})
    assert resposta.status_code == 200
    nomes = [d["nome"] for d in resposta.json()]
    assert nomes == ["Doc fiscal"]


def test_atualizar_documento(client, usuario_autenticado):
    criado = client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf(),
        data={"categoria": "fiscal", "nome": "Nome original"},
    ).json()

    resposta = client.put(
        f"/documentos/{criado['id']}",
        headers=usuario_autenticado,
        json={"nome": "Nome atualizado", "data_validade": "2030-01-01T00:00:00"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Nome atualizado"
    assert corpo["status"] == "valida"


def test_atualizar_documento_categoria_invalida_retorna_400(client, usuario_autenticado):
    criado = client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf(),
        data={"categoria": "fiscal", "nome": "Doc"},
    ).json()

    resposta = client.put(
        f"/documentos/{criado['id']}", headers=usuario_autenticado, json={"categoria": "invalida"}
    )
    assert resposta.status_code == 400


def test_atualizar_documento_inexistente_retorna_404(client, usuario_autenticado):
    resposta = client.put("/documentos/999999", headers=usuario_autenticado, json={"nome": "X"})
    assert resposta.status_code == 404


def test_substituir_documento_arquiva_versao_anterior_no_historico(client, usuario_autenticado):
    criado = client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf("v1.pdf"),
        data={"categoria": "fiscal", "nome": "Certidão"},
    ).json()

    resposta_substituir = client.post(
        f"/documentos/{criado['id']}/substituir",
        headers=usuario_autenticado,
        files=_arquivo_pdf("v2.pdf"),
    )
    assert resposta_substituir.status_code == 200
    assert resposta_substituir.json()["nome_arquivo_original"] == "v2.pdf"

    resposta_historico = client.get(
        "/documentos/historico", headers=usuario_autenticado, params={"documento_id": criado["id"]}
    )
    assert resposta_historico.status_code == 200
    historico = resposta_historico.json()
    assert len(historico) == 1
    assert historico[0]["nome_arquivo_original"] == "v1.pdf"


def test_substituir_documento_inexistente_retorna_404(client, usuario_autenticado):
    resposta = client.post(
        "/documentos/999999/substituir", headers=usuario_autenticado, files=_arquivo_pdf()
    )
    assert resposta.status_code == 404


def test_baixar_arquivo_do_documento(client, usuario_autenticado):
    criado = client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf(),
        data={"categoria": "fiscal", "nome": "Certidão"},
    ).json()

    resposta = client.get(f"/documentos/{criado['id']}/arquivo", headers=usuario_autenticado)
    assert resposta.status_code == 200
    assert resposta.content == b"%PDF-1.4 conteudo fake de teste"


def test_remover_documento(client, usuario_autenticado):
    criado = client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf(),
        data={"categoria": "fiscal", "nome": "Certidão"},
    ).json()

    resposta_remover = client.delete(f"/documentos/{criado['id']}", headers=usuario_autenticado)
    assert resposta_remover.status_code == 204

    resposta_lista = client.get("/documentos", headers=usuario_autenticado)
    assert resposta_lista.json() == []


def test_indicadores_documentos(client, usuario_autenticado):
    client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf("a.pdf"),
        data={"categoria": "fiscal", "nome": "Doc A"},
    )
    client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf("b.pdf"),
        data={"categoria": "juridica", "nome": "Doc B"},
    )

    resposta = client.get("/documentos/indicadores", headers=usuario_autenticado)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert sum(item["quantidade"] for item in corpo["por_status"]) == 2
    categorias = {item["chave"] for item in corpo["por_categoria"]}
    assert categorias == {"fiscal", "juridica"}
    assert len(corpo["ultimas_atualizacoes"]) == 2


def test_documentos_de_uma_empresa_nao_aparecem_para_outra(client, usuario_autenticado):
    client.post(
        "/documentos",
        headers=usuario_autenticado,
        files=_arquivo_pdf(),
        data={"categoria": "fiscal", "nome": "Doc da empresa 1"},
    )

    client.post(
        "/auth/registrar",
        json={"email": "outra.empresa@example.com", "senha": "senha-123456", "nome_empresa": "Empresa 2"},
    )
    login = client.post(
        "/auth/login", data={"username": "outra.empresa@example.com", "password": "senha-123456"}
    )
    headers_outra_empresa = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resposta = client.get("/documentos", headers=headers_outra_empresa)
    assert resposta.json() == []


def test_documentos_exigem_autenticacao(client):
    assert client.get("/documentos").status_code == 401
    assert client.get("/documentos/indicadores").status_code == 401
    assert client.post("/documentos", files=_arquivo_pdf(), data={"categoria": "fiscal", "nome": "X"}).status_code == 401
