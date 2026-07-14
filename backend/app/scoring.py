"""
Motor de filtro/pontuação — mesma lógica já validada nas fases anteriores,
mas agora recebendo os parâmetros de um Criterio específico, em vez de
valores fixos. Isso é o que permite cada cliente ter seus próprios filtros
rodando sobre a MESMA base de licitações coletadas.
"""

import re
import unicodedata
from datetime import datetime, date

from . import models


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def aplicar_criterio(licitacao: models.Licitacao, criterio: models.Criterio) -> tuple[bool, list[str], float]:
    """Retorna (passou, motivos, score) para uma licitação em relação a um critério."""
    motivos = []

    texto_completo = normalizar((licitacao.objeto or "") + " " + (licitacao.informacao_complementar or ""))

    # 1. Palavra-chave obrigatória
    if normalizar(criterio.palavra_obrigatoria) not in texto_completo:
        return False, [], 0
    motivos.append(f"Contém: '{criterio.palavra_obrigatoria}'")

    # 2. Palavras-chave bônus
    bonus_lista = [p.strip() for p in (criterio.palavras_bonus or "").split(",") if p.strip()]
    bonus_hits = [p for p in bonus_lista if normalizar(p) in texto_completo]
    if bonus_hits:
        motivos.append("Também menciona: " + ", ".join(bonus_hits))

    # 3. Valor estimado
    valor = licitacao.valor_estimado or 0
    if valor <= 0:
        return False, [], 0
    if valor < criterio.valor_minimo or valor > criterio.valor_maximo:
        return False, [], 0
    motivos.append(f"Valor: R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # 4. Estados permitidos (vazio = aceita todos)
    estados_lista = [e.strip().upper() for e in (criterio.estados_permitidos or "").split(",") if e.strip()]
    if estados_lista and (licitacao.uf or "").upper() not in estados_lista:
        return False, [], 0
    if estados_lista:
        motivos.append(f"Estado: {licitacao.uf}")

    # 5. Dedicação exclusiva de mão de obra
    if criterio.exigir_dedicacao_exclusiva:
        tem_demo = ("dedicacao exclusiva" in texto_completo) or ("demo" in texto_completo)
        if not tem_demo:
            return False, [], 0
        motivos.append("DEMO: sim")

    # 6. Modalidade Pregão
    if criterio.exigir_pregao:
        modalidade_norm = normalizar(licitacao.modalidade or "")
        if "pregao" not in modalidade_norm:
            return False, [], 0
        motivos.append(f"Modalidade: {licitacao.modalidade}")

    # Pontuação
    score = 30 + len(bonus_hits) * 15
    if valor > 0:
        score += min(valor / 1_000_000, 20)
    if estados_lista and (licitacao.uf or "").upper() == estados_lista[0]:
        score += 10  # pequeno bônus por ser o estado "principal" do critério

    return True, motivos, score