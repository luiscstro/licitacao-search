"""
Diagnóstico: por que a busca está vindo vazia?

Roda isso na pasta `backend`:
    python diagnostico_busca.py

Não mexe em nada, só mostra informação.
"""

import sqlite3

conn = sqlite3.connect("licitacoes_saas.db")

print("=" * 60)
print("1. Quantas linhas tem no total?")
print("=" * 60)
total = conn.execute("SELECT COUNT(*) FROM licitacoes").fetchone()[0]
print(f"Total: {total}")

print()
print("=" * 60)
print("2. Quantas estão ATIVAS (é isso que a busca considera)?")
print("=" * 60)
ativas = conn.execute("SELECT COUNT(*) FROM licitacoes WHERE ativa = 1").fetchone()[0]
print(f"Ativas: {ativas}")

print()
print("=" * 60)
print("3. Como está o texto_busca de 3 exemplos (deve estar minúsculo, sem acento)?")
print("=" * 60)
exemplos = conn.execute("SELECT objeto, texto_busca FROM licitacoes LIMIT 3").fetchall()
for objeto, texto_busca in exemplos:
    print(f"\nOBJETO ORIGINAL: {objeto[:150]}")
    print(f"TEXTO_BUSCA:      {(texto_busca or '(vazio!)')[:150]}")

print()
print("=" * 60)
print("4. Quantas linhas têm 'apoio administrativo' no texto_busca (busca direta no banco)?")
print("=" * 60)
contagem_direta = conn.execute(
    "SELECT COUNT(*) FROM licitacoes WHERE texto_busca LIKE '%apoio administrativo%'"
).fetchone()[0]
print(f"Contendo 'apoio administrativo': {contagem_direta}")

print()
print("=" * 60)
print("5. Quantas linhas têm só 'apoio' (mais genérico, pra confirmar que a coluna tem conteúdo)?")
print("=" * 60)
contagem_generica = conn.execute(
    "SELECT COUNT(*) FROM licitacoes WHERE texto_busca LIKE '%apoio%'"
).fetchone()[0]
print(f"Contendo 'apoio': {contagem_generica}")

print()
print("=" * 60)
print("6. Quantas linhas têm texto_busca vazio ou nulo (sinal de coleta incompleta)?")
print("=" * 60)
vazias = conn.execute(
    "SELECT COUNT(*) FROM licitacoes WHERE texto_busca IS NULL OR texto_busca = ''"
).fetchone()[0]
print(f"Com texto_busca vazio: {vazias}")

conn.close()

print()
print("=" * 60)
print("Manda esse resultado inteiro de volta — isso vai dizer exatamente onde está o problema.")
print("=" * 60)