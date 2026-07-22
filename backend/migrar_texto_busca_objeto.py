#!/usr/bin/env python3
"""
Migração única: adiciona a coluna `texto_busca_objeto` e recalcula ela
pra todas as licitações que JÁ ESTÃO no seu banco — sem precisar buscar
nada de novo no PNCP (usa o `objeto` e `informacao_complementar` que já
estão salvos localmente).

Rode isso UMA VEZ depois de atualizar os arquivos do backend:
    cd backend
    python3 migrar_texto_busca_objeto.py

Depois disso pode rodar a API normalmente — não precisa rodar o
collector_pncp.py de novo por causa dessa mudança específica.
"""

import sqlite3
import sys

sys.path.insert(0, ".")
from app.scoring import montar_texto_busca_objeto
from app.database import DATABASE_URL

if not DATABASE_URL.startswith("sqlite"):
    print("Esse script assume SQLite. Se você já migrou pra outro banco, adapte antes de rodar.")
    sys.exit(1)

caminho_db = DATABASE_URL.replace("sqlite:///", "")

conn = sqlite3.connect(caminho_db)
cur = conn.cursor()

# 1. Adiciona a coluna se ainda não existir
cur.execute("PRAGMA table_info(licitacoes)")
colunas_existentes = {linha[1] for linha in cur.fetchall()}

if "texto_busca_objeto" not in colunas_existentes:
    print("Adicionando coluna texto_busca_objeto...")
    cur.execute("ALTER TABLE licitacoes ADD COLUMN texto_busca_objeto TEXT DEFAULT ''")
    conn.commit()
else:
    print("Coluna texto_busca_objeto já existe, só vou recalcular os valores.")

# 2. Recalcula o valor pra cada linha, usando o que já está salvo (sem PNCP)
cur.execute("SELECT numero_controle, objeto, informacao_complementar FROM licitacoes")
linhas = cur.fetchall()
print(f"Recalculando {len(linhas)} registros...")

atualizados = 0
for numero_controle, objeto, informacao_complementar in linhas:
    novo_valor = montar_texto_busca_objeto(objeto or "", informacao_complementar or "")
    cur.execute(
        "UPDATE licitacoes SET texto_busca_objeto = ? WHERE numero_controle = ?",
        (novo_valor, numero_controle),
    )
    atualizados += 1
    if atualizados % 2000 == 0:
        print(f"  {atualizados}/{len(linhas)}...")
        conn.commit()

conn.commit()
conn.close()

print(f"\n✅ Migração concluída — {atualizados} registros atualizados.")
print("Agora pode subir a API normalmente (uvicorn app.main:app --reload).")