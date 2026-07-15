"""
Motor de filtro/pontuação. Duas formas de uma licitação "passar":

1. Bater com um Criterio salvo pela empresa (aplicar_criterio) — como já
   funcionava antes.
2. Bater com uma busca avançada ad-hoc (aplicar_busca_avancada) — texto
   livre + filtros soltos (UF, valor, órgão, datas), sem precisar de
   critério salvo. Usada pela busca livre e pela busca "dentro dos
   resultados já filtrados" (as duas se combinam).
"""

import unicodedata
from datetime import datetime

from . import models


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def aplicar_criterio(licitacao: models.Licitacao, criterio: models.Criterio) -> tuple[bool, list[str], float]:
    """Retorna (passou, motivos, score) para uma licitação em relação a um critério salvo."""
    motivos = []

    texto_completo = normalizar((licitacao.objeto or "") + " " + (licitacao.informacao_complementar or ""))

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

    if criterio.exigir_pregao:
        modalidade_norm = normalizar(licitacao.modalidade or "")
        if "pregao" not in modalidade_norm:
            return False, [], 0
        motivos.append(f"Modalidade: {licitacao.modalidade}")

    score = 30 + len(bonus_hits) * 15
    if valor > 0:
        score += min(valor / 1_000_000, 20)
    if estados_lista and (licitacao.uf or "").upper() == estados_lista[0]:
        score += 10

    return True, motivos, score


def aplicar_filtros_avancados(
    licitacao: models.Licitacao,
    busca: str | None = None,
    uf: str | None = None,
    orgao: str | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    data_de: str | None = None,
    data_ate: str | None = None,
) -> bool:
    """
    Filtros soltos, aplicados independentemente de qualquer critério salvo.
    Retorna só True/False — usado tanto pra 'busca livre' (sem critério)
    quanto pra refinar resultados que já passaram por um critério.
    """
    if busca:
        texto_completo = normalizar(
            (licitacao.objeto or "") + " " + (licitacao.orgao or "") + " " + (licitacao.cidade or "")
        )
        if normalizar(busca) not in texto_completo:
            return False

    if uf and (licitacao.uf or "").upper() != uf.upper():
        return False

    if orgao and normalizar(orgao) not in normalizar(licitacao.orgao or ""):
        return False

    valor = licitacao.valor_estimado or 0
    if valor_min is not None and valor < valor_min:
        return False
    if valor_max is not None and valor > valor_max:
        return False

    data_referencia = licitacao.data_encerramento_proposta or licitacao.data_abertura_proposta
    if (data_de or data_ate) and data_referencia:
        try:
            data_lic = datetime.fromisoformat(data_referencia).date()
            if data_de and data_lic < datetime.fromisoformat(data_de).date():
                return False
            if data_ate and data_lic > datetime.fromisoformat(data_ate).date():
                return False
        except ValueError:
            pass

    return True