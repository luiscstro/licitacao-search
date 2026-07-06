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
            ativa INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

def salvar_resultado_da_rodada(itens_aprovados: list[tuple]):
    from buscar_licitacoes import montar_link_edital

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
                link_edital, score, motivos, primeira_vez_vista, ultima_vez_vista, ativa
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
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
        "SELECT COUNT(*) as n FROM licitacoes WHERE primeira_vez_vista = ultima_vez_vista AND ativa = 1"
    ).fetchone()["n"]
    total_ativas = conn.execute("SELECT COUNT(*) as n FROM licitacoes WHERE ativa = 1").fetchone()["n"]

    conn.close()
    return {"novas_nesta_rodada": novas, "total_ativas": total_ativas}

def listar_ativas() -> list[dict]:
    conn = conectar()
    linhas = conn.execute(
        "SELECT * FROM licitacoes WHERE ativa = 1 ORDER BY score DESC"
    ).fetchall()
    conn.close()
    return [dict(linha) for linha in linhas]

def eh_nova(licitacao_row: dict) -> bool:
    return licitacao_row["primeira_vez_vista"] == licitacao_row["ultima_vez_vista"]