#!/usr/bin/env python3
"""
Migração única: adiciona os campos do cadastro único da empresa (CNPJ,
inscrições, endereço, representante legal, situação cadastral) na tabela
`empresas`, pro módulo de Gestão de Documentos e Certidões.

Rode isso UMA VEZ depois de atualizar os arquivos do backend:
    cd backend
    python3 migrations/migrar_dados_empresa.py

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

cur.execute("PRAGMA table_info(empresas)")
colunas_existentes = {linha[1] for linha in cur.fetchall()}

COLUNAS_NOVAS = [
    ("cnpj", "TEXT"),
    ("inscricao_estadual", "TEXT"),
    ("inscricao_municipal", "TEXT"),
    ("endereco_logradouro", "TEXT"),
    ("endereco_numero", "TEXT"),
    ("endereco_complemento", "TEXT"),
    ("endereco_bairro", "TEXT"),
    ("endereco_cidade", "TEXT"),
    ("endereco_uf", "TEXT"),
    ("endereco_cep", "TEXT"),
    ("representante_nome", "TEXT"),
    ("representante_cpf", "TEXT"),
    ("representante_cargo", "TEXT"),
    ("representante_email", "TEXT"),
    ("representante_telefone", "TEXT"),
    ("situacao_cadastral", "TEXT"),
    ("cnpj_sincronizado_em", "DATETIME"),
]

adicionadas = 0
for nome_coluna, tipo in COLUNAS_NOVAS:
    if nome_coluna not in colunas_existentes:
        print(f"Adicionando coluna {nome_coluna}...")
        cur.execute(f"ALTER TABLE empresas ADD COLUMN {nome_coluna} {tipo}")
        adicionadas += 1

if adicionadas:
    conn.commit()
    print(f"✅ {adicionadas} coluna(s) adicionada(s) em 'empresas'.")
else:
    print("Todas as colunas já existem, nada a fazer.")

conn.close()
