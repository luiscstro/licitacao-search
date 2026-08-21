"""Testes unitários pra app/scoring.py — motor de filtro/pontuação."""

from types import SimpleNamespace

from app import scoring

# ---------- normalizar ----------


def test_normalizar_remove_acentos_e_minusculiza():
    assert scoring.normalizar("Serviço de Limpeza") == "servico de limpeza"


def test_normalizar_string_vazia():
    assert scoring.normalizar("") == ""
    assert scoring.normalizar(None) == ""


# ---------- montar_texto_busca_objeto / montar_texto_busca ----------


def test_montar_texto_busca_objeto_nao_inclui_orgao():
    texto = scoring.montar_texto_busca_objeto("Aquisição de material de limpeza", "urgente")
    assert "material de limpeza" in texto
    assert "urgente" in texto


def test_montar_texto_busca_inclui_orgao_e_cidade():
    texto = scoring.montar_texto_busca("objeto qualquer", "Prefeitura de Teste", "São Paulo", "")
    assert "prefeitura de teste" in texto
    assert "sao paulo" in texto


# ---------- bate_modalidade ----------


def test_bate_modalidade_vazio_aceita_qualquer():
    assert scoring.bate_modalidade("Pregão Eletrônico", "") is True


def test_bate_modalidade_bate_um_dos_trechos():
    assert scoring.bate_modalidade("Pregão Eletrônico", "Dispensa,Pregão") is True


def test_bate_modalidade_nao_bate():
    assert scoring.bate_modalidade("Concorrência", "Dispensa,Pregão") is False


# ---------- aplicar_criterio ----------


def _licitacao(**kwargs):
    padrao = dict(
        texto_busca_objeto="apoio administrativo e limpeza dedicacao exclusiva",
        valor_estimado=500_000,
        uf="SP",
        modalidade="Pregão Eletrônico",
    )
    padrao.update(kwargs)
    return SimpleNamespace(**padrao)


def _criterio(**kwargs):
    padrao = dict(
        palavra_obrigatoria="apoio administrativo",
        palavras_bonus="",
        valor_minimo=0,
        valor_maximo=999_999_999,
        estados_permitidos="",
        exigir_dedicacao_exclusiva=False,
        modalidades_permitidas="",
    )
    padrao.update(kwargs)
    return SimpleNamespace(**padrao)


def test_aplicar_criterio_passa_com_palavra_obrigatoria():
    passou, motivos, score = scoring.aplicar_criterio(_licitacao(), _criterio())
    assert passou is True
    assert score > 0
    assert any("apoio administrativo" in m for m in motivos)


def test_aplicar_criterio_falha_sem_palavra_obrigatoria():
    licitacao = _licitacao(texto_busca_objeto="compra de veiculos novos")
    passou, motivos, score = scoring.aplicar_criterio(licitacao, _criterio())
    assert passou is False
    assert score == 0
    assert motivos == []


def test_aplicar_criterio_falha_por_valor_fora_da_faixa():
    criterio = _criterio(valor_minimo=1_000_000, valor_maximo=2_000_000)
    passou, _, score = scoring.aplicar_criterio(_licitacao(), criterio)
    assert passou is False
    assert score == 0


def test_aplicar_criterio_falha_por_estado_nao_permitido():
    criterio = _criterio(estados_permitidos="RJ,MG")
    passou, _, _ = scoring.aplicar_criterio(_licitacao(uf="SP"), criterio)
    assert passou is False


def test_aplicar_criterio_exige_dedicacao_exclusiva():
    criterio = _criterio(exigir_dedicacao_exclusiva=True)
    licitacao_sem_demo = _licitacao(texto_busca_objeto="apoio administrativo simples")
    passou, _, _ = scoring.aplicar_criterio(licitacao_sem_demo, criterio)
    assert passou is False

    licitacao_com_demo = _licitacao(texto_busca_objeto="apoio administrativo com dedicacao exclusiva")
    passou, motivos, _ = scoring.aplicar_criterio(licitacao_com_demo, criterio)
    assert passou is True
    assert any("DEMO" in m for m in motivos)


def test_aplicar_criterio_bonus_aumenta_score():
    criterio_sem_bonus = _criterio()
    criterio_com_bonus = _criterio(palavras_bonus="limpeza")

    _, _, score_sem_bonus = scoring.aplicar_criterio(_licitacao(), criterio_sem_bonus)
    _, _, score_com_bonus = scoring.aplicar_criterio(_licitacao(), criterio_com_bonus)

    assert score_com_bonus > score_sem_bonus


def test_aplicar_criterio_sem_palavra_obrigatoria_no_criterio_falha():
    criterio = _criterio(palavra_obrigatoria="")
    passou, motivos, score = scoring.aplicar_criterio(_licitacao(), criterio)
    assert passou is False
    assert motivos == []
    assert score == 0


# ---------- aplicar_filtros_avancados ----------


def test_aplicar_filtros_avancados_sem_busca_sempre_passa():
    licitacao = SimpleNamespace(texto_busca="qualquer coisa")
    assert scoring.aplicar_filtros_avancados(licitacao, None) is True


def test_aplicar_filtros_avancados_busca_bate():
    licitacao = SimpleNamespace(texto_busca="compra de material de limpeza urbana")
    assert scoring.aplicar_filtros_avancados(licitacao, "limpeza") is True


def test_aplicar_filtros_avancados_busca_nao_bate():
    licitacao = SimpleNamespace(texto_busca="compra de veiculos novos")
    assert scoring.aplicar_filtros_avancados(licitacao, "limpeza") is False
