"""
Motor de filtro/pontuação.

Duas formas de uma licitação "passar":
1. Bater com um Criterio salvo pela empresa (aplicar_criterio)
2. Bater com uma busca avançada ad-hoc (aplicar_filtros_avancados) — texto
   livre + filtros soltos, sem precisar de critério salvo

Ambas usam o campo `texto_busca` (já normalizado — minúsculo, sem acento
— calculado uma vez pelo coletor) em vez de reprocessar o texto a cada
consulta. Isso é o que permite a busca continuar rápida mesmo com uma
base nacional bem maior.
"""

import unicodedata


def normalizar(texto: str) -> str:
    """Usado pelo coletor pra gerar o texto_busca, e pelas buscas pra
    normalizar o termo de pesquisa do mesmo jeito."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def montar_texto_busca(objeto: str, orgao: str, cidade: str, informacao_complementar: str = "") -> str:
    """Concatena e normaliza os campos relevantes — chamado pelo coletor
    ao salvar cada licitação, uma vez só, em vez de toda hora numa busca."""
    return normalizar(f"{objeto or ''} {orgao or ''} {cidade or ''} {informacao_complementar or ''}")


def bate_modalidade(modalidade_licitacao: str, modalidades_permitidas: str) -> bool:
    """modalidades_permitidas é uma lista separada por vírgula de trechos
    (ex: 'Pregão,Dispensa'). Vazio = aceita qualquer modalidade. Basta UM
    dos trechos aparecer no nome da modalidade da licitação."""
    permitidas = [m.strip() for m in (modalidades_permitidas or "").split(",") if m.strip()]
    if not permitidas:
        return True
    modalidade_norm = normalizar(modalidade_licitacao or "")
    return any(normalizar(m) in modalidade_norm for m in permitidas)


def aplicar_criterio(licitacao, criterio) -> tuple[bool, list[str], float]:
    """Retorna (passou, motivos, score) para uma licitação em relação a um critério salvo.
    Assume que `licitacao` já passou pelo pré-filtro SQL (ver main.py) — aqui só
    confere as regras que não dá pra expressar bem em SQL (modalidade por trecho,
    combinação de bônus etc.) e monta a lista de motivos."""
    motivos = []
    texto_completo = licitacao.texto_busca or ""

    if normalizar(criterio.palavra_obrigatoria) not in texto_completo:
        return False, [], 0
    motivos.append(f"Contém: '{criterio.palavra_obrigatoria}'")

    bonus_lista = [p.strip() for p in (criterio.palavras_bonus or "").split(",") if p.strip()]
    bonus_hits = [p for p in bonus_lista if normalizar(p) in texto_completo]
    if bonus_hits:
        motivos.append("Também menciona: " + ", ".join(bonus_hits))

    valor = licitacao.valor_estimado or 0
    if valor <= 0:
        return False, [], 0
    if valor < criterio.valor_minimo or valor > criterio.valor_maximo:
        return False, [], 0
    motivos.append(f"Valor: R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    estados_lista = [e.strip().upper() for e in (criterio.estados_permitidos or "").split(",") if e.strip()]
    if estados_lista and (licitacao.uf or "").upper() not in estados_lista:
        return False, [], 0
    if estados_lista:
        motivos.append(f"Estado: {licitacao.uf}")

    if criterio.exigir_dedicacao_exclusiva:
        tem_demo = ("dedicacao exclusiva" in texto_completo) or ("demo" in texto_completo)
        if not tem_demo:
            return False, [], 0
        motivos.append("DEMO: sim")

    if not bate_modalidade(licitacao.modalidade, criterio.modalidades_permitidas):
        return False, [], 0
    if criterio.modalidades_permitidas:
        motivos.append(f"Modalidade: {licitacao.modalidade}")

    score = 30 + len(bonus_hits) * 15
    if valor > 0:
        score += min(valor / 1_000_000, 20)
    if estados_lista and (licitacao.uf or "").upper() == estados_lista[0]:
        score += 10

    return True, motivos, score


def aplicar_filtros_avancados(licitacao, busca: str | None = None) -> bool:
    """Confere só o texto livre — os outros filtros (uf, valor, datas, órgão)
    já são aplicados via SQL antes de chegar aqui (ver main.py)."""
    if busca:
        if normalizar(busca) not in (licitacao.texto_busca or ""):
            return False
    return True