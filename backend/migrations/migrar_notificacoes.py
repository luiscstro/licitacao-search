#!/usr/bin/env python3
"""
Migração única: adiciona a coluna `receber_notificacoes` na tabela `users`
(default = ligado), pra suportar o resumo diário de licitações por e-mail.

Rode isso UMA VEZ depois de atualizar os arquivos do backend:
    cd backend
    python3 migrar_notificacoes.py

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

cur.execute("PRAGMA table_info(users)")
colunas_existentes = {linha[1] for linha in cur.fetchall()}

if "receber_notificacoes" not in colunas_existentes:
    print("Adicionando coluna receber_notificacoes...")
    cur.execute("ALTER TABLE users ADD COLUMN receber_notificacoes BOOLEAN DEFAULT 1")
    conn.commit()
    print("✅ Coluna adicionada — todos os usuários já existentes ficam com notificações ligadas por padrão.")
else:
    print("Coluna receber_notificacoes já existe, nada a fazer.")

conn.close()
