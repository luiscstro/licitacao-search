"""
Módulo de banco de dados - Buscador de Licitações
====================================================

Usa SQLite (arquivo local, sem precisar instalar servidor de banco).
Guarda o histórico de licitações encontradas, controla quais ainda
estão "ativas" (ainda aparecem nas buscas mais recentes) e quais somem
(prazo encerrou ou foram retiradas), e marca quais são novas em cada rodada.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

CAMINHO_DB = Path(__file__).parent / "licitacoes.db"


def conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(CAMINHO_DB)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
    """Cria a tabela se ela ainda não existir. Seguro rodar várias vezes."""
    conn = conectar()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS licitacoes (
            numero_controle TEXT PRIMARY KEY,
            orgao TEXT,
            cidade TEXT,
            uf TEXT,
            objeto TEXT,
            valor_estimado REAL,
            modalidade TEXT,
            data_abertura_proposta TEXT,
            data_encerramento_proposta TEXT,
            link_edital TEXT,
            score REAL,
            motivos TEXT,
            primeira_vez_vista TEXT,
            ultima_vez_vista TEXT,
            vezes_vista INTEGER DEFAULT 1,
            ativa INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def salvar_resultado_da_rodada(itens_aprovados: list[tuple]):
    """
    Recebe a lista de (contratacao_dict, motivos, score) que passou nos filtros
    NESTA rodada, e sincroniza com o banco:
    - Item novo -> insere com primeira_vez_vista = agora
    - Item que já existia -> atualiza dados e ultima_vez_vista, mantém primeira_vez_vista
    - Item que existia mas NÃO veio nesta rodada -> marca ativa = 0
      (proposta provavelmente encerrou ou saiu dos critérios)
    """
    from buscar_licitacoes_pncp import montar_link_edital  # import local pra evitar ciclo

    conn = conectar()
    agora = datetime.now().isoformat(timespec="seconds")

    ids_desta_rodada = set()

    for contratacao, motivos, score in itens_aprovados:
        numero_controle = contratacao["numeroControlePNCP"]
        ids_desta_rodada.add(numero_controle)

        orgao_info = contratacao.get("orgaoEntidade") or {}
        unidade = contratacao.get("unidadeOrgao") or {}

        existente = conn.execute(
            "SELECT primeira_vez_vista FROM licitacoes WHERE numero_controle = ?",
            (numero_controle,)
        ).fetchone()

        primeira_vez_vista = existente["primeira_vez_vista"] if existente else agora

        conn.execute("""
            INSERT INTO licitacoes (
                numero_controle, orgao, cidade, uf, objeto, valor_estimado,
                modalidade, data_abertura_proposta, data_encerramento_proposta,
                link_edital, score, motivos, primeira_vez_vista, ultima_vez_vista,
                vezes_vista, ativa
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
            ON CONFLICT(numero_controle) DO UPDATE SET
                orgao=excluded.orgao,
                cidade=excluded.cidade,
                uf=excluded.uf,
                objeto=excluded.objeto,
                valor_estimado=excluded.valor_estimado,
                modalidade=excluded.modalidade,
                data_abertura_proposta=excluded.data_abertura_proposta,
                data_encerramento_proposta=excluded.data_encerramento_proposta,
                link_edital=excluded.link_edital,
                score=excluded.score,
                motivos=excluded.motivos,
                ultima_vez_vista=excluded.ultima_vez_vista,
                vezes_vista=licitacoes.vezes_vista + 1,
                ativa=1
        """, (
            numero_controle,
            orgao_info.get("razaosocial", "—"),
            unidade.get("municipioNome", "—"),
            unidade.get("ufSigla", "—"),
            contratacao.get("objetoCompra", ""),
            contratacao.get("valorTotalEstimado") or 0,
            contratacao.get("modalidadeNome", "—"),
            contratacao.get("dataAberturaProposta"),
            contratacao.get("dataEncerramentoProposta"),
            montar_link_edital(contratacao),
            score,
            json.dumps(motivos, ensure_ascii=False),
            primeira_vez_vista,
            agora,
        ))

    # Marca como inativas as que não vieram nesta rodada
    if ids_desta_rodada:
        placeholders = ",".join("?" * len(ids_desta_rodada))
        conn.execute(
            f"UPDATE licitacoes SET ativa = 0 WHERE numero_controle NOT IN ({placeholders})",
            list(ids_desta_rodada)
        )
    else:
        conn.execute("UPDATE licitacoes SET ativa = 0")

    conn.commit()

    novas = conn.execute(
        "SELECT COUNT(*) as n FROM licitacoes WHERE vezes_vista = 1 AND ativa = 1"
    ).fetchone()["n"]
    total_ativas = conn.execute("SELECT COUNT(*) as n FROM licitacoes WHERE ativa = 1").fetchone()["n"]

    conn.close()
    return {"novas_nesta_rodada": novas, "total_ativas": total_ativas}


def listar_ativas() -> list[dict]:
    """Retorna todas as licitações atualmente ativas, ordenadas por score."""
    conn = conectar()
    linhas = conn.execute(
        "SELECT * FROM licitacoes WHERE ativa = 1 ORDER BY score DESC"
    ).fetchall()
    conn.close()
    return [dict(linha) for linha in linhas]


def eh_nova(licitacao_row: dict) -> bool:
    """Considera 'nova' se essa é a primeira vez que essa licitação foi vista (nunca em rodadas anteriores)."""
    return licitacao_row["vezes_vista"] == 1