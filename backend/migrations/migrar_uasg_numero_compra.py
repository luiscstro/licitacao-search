#!/usr/bin/env python3
"""
Migração única: adiciona as colunas `codigo_unidade` (UASG/unidade
administrativa) e `numero_compra` (número do pregão/contratação) na tabela
`licitacoes`.

Registros já coletados ficam com esses campos vazios até o coletor rodar de
novo (`collector_pncp.py` já foi atualizado pra gravar os dois a partir de
agora) — não tem como preencher retroativamente sem reconsultar o PNCP.

Rode isso UMA VEZ depois de atualizar os arquivos do backend:
    cd backend
    python3 migrations/migrar_uasg_numero_compra.py

Depois disso pode subir a API normalmente (uvicorn app.main:app --reload).
"""

import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, ".")
from app.database import DATABASE_URL

if not DATABASE_URL.startswith("sqlite"):
    print("Esse script assume SQLite. Se você já migrou pra outro banco, adapte antes de rodar.")
    sys.exit(1)

caminho_db = DATABASE_URL.replace("sqlite:///", "")

conn = sqlite3.connect(caminho_db)
cur = conn.cursor()

cur.execute("PRAGMA table_info(licitacoes)")
colunas_existentes = {linha[1] for linha in cur.fetchall()}

COLUNAS_NOVAS = [
    ("codigo_unidade", "TEXT"),
    ("numero_compra", "TEXT"),
]

adicionadas = 0
for nome_coluna, tipo in COLUNAS_NOVAS:
    if nome_coluna not in colunas_existentes:
        print(f"Adicionando coluna {nome_coluna}...")
        cur.execute(f"ALTER TABLE licitacoes ADD COLUMN {nome_coluna} {tipo}")
        adicionadas += 1

if adicionadas:
    conn.commit()
    print(f"✅ {adicionadas} coluna(s) adicionada(s) em 'licitacoes'.")
    print("Rode o coletor (collector_pncp.py) pra preencher os valores nas licitações já salvas.")
else:
    print("Todas as colunas já existem, nada a fazer.")

conn.close()
