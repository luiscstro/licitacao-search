"""
Confere quantas licitações existem POR MODALIDADE no seu banco —
ajuda a identificar se alguma modalidade específica não foi coletada
por completo (ex: Pregão Eletrônico deveria ter uns 15-20 mil itens
sozinho, se tiver bem menos que isso, a coleta provavelmente parou
no meio).

Roda na pasta backend:
    python contar_por_modalidade.py
"""

import sqlite3

conn = sqlite3.connect("licitacoes_saas.db")

print("=" * 60)
print("Total de licitações por modalidade:")
print("=" * 60)

linhas = conn.execute("""
    SELECT modalidade, COUNT(*) as total
    FROM licitacoes
    GROUP BY modalidade
    ORDER BY total DESC
""").fetchall()

for modalidade, total in linhas:
    print(f"{total:>8}  {modalidade}")

print()
print("=" * 60)
print("Total geral:", sum(t for _, t in linhas))
print("=" * 60)

print()
print("=" * 60)
print("Licitações por estado (top 10):")
print("=" * 60)
linhas_uf = conn.execute("""
    SELECT uf, COUNT(*) as total
    FROM licitacoes
    GROUP BY uf
    ORDER BY total DESC
    LIMIT 10
""").fetchall()
for uf, total in linhas_uf:
    print(f"{total:>8}  {uf}")

print()
print("=" * 60)
print("Quantas licitações tem no Maranhão (MA), de qualquer modalidade:")
print("=" * 60)
total_ma = conn.execute("SELECT COUNT(*) FROM licitacoes WHERE uf = 'MA'").fetchone()[0]
print(f"MA: {total_ma}")

conn.close()