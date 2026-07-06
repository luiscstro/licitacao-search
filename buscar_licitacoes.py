#!/usr/bin/env python3
"""
Buscador automático de licitações - PNCP (Portal Nacional de Contratações Públicas)
=====================================================================================

Diferente da versão anterior (ConLicitação), esse script usa a API OFICIAL e
PÚBLICA do governo. Não precisa de login, cookie, nem nada — só rodar.

Fonte oficial: https://pncp.gov.br/api/consulta
Documentação: Manual PNCP API Consultas - Versão 1.0

Como usar:
    1. pip install requests
    2. python3 buscar_licitacoes.py
    3. Abra o arquivo licitacoes.html que foi gerado

Esse script não depende de sessão/cookie — pode ser agendado pra rodar
automaticamente (cron, GitHub Actions, etc.) sem manutenção.
"""

import re
import json
import time
import unicodedata
from datetime import datetime, date, timedelta
from pathlib import Path

import requests

# ============================================================
# CONFIGURAÇÃO — edite aqui conforme sua necessidade
# ============================================================

# Palavras-chave que definem uma licitação de interesse
KEYWORDS = ["apoio administrativo", "limpeza", "recepção", "recepcionista", "copeiragem"]

# Valor estimado máximo aceito (R$)
VALOR_MAXIMO = 20_000_000.00

# Estados aceitos (região próxima a São Luís/MA)
ESTADOS_PERMITIDOS = ["MA", "PI", "PA", "TO", "CE"]

# Só aceitar licitações cujo texto mencione dedicação exclusiva de mão de obra
EXIGIR_DEDICACAO_EXCLUSIVA = True

# Códigos de modalidade a buscar (vide tabela de domínio do PNCP).
# 6 = Pregão Eletrônico | 7 = Pregão Presencial
MODALIDADES = [6]

# Não aceitar licitações cujo prazo de proposta encerre hoje
EXCLUIR_PRAZO_HOJE = True

# Até quantos dias no futuro buscar contratações com proposta em aberto
JANELA_DIAS = 60

BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
TAMANHO_PAGINA = 20
PAUSA_ENTRE_REQUISICOES = 1.5  # segundos entre cada requisição — educado com o servidor público
MAX_TENTATIVAS = 6  # quantas vezes tenta de novo se receber 429 (rate limit)
ESPERA_INICIAL_RETRY = 5  # segundos — dobra a cada nova tentativa (5, 10, 20, 40...)

# ============================================================
# LÓGICA — normalmente não precisa mexer daqui pra baixo
# ============================================================


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def buscar_pagina(session: requests.Session, uf: str, modalidade: int, data_final: str, pagina: int) -> dict:
    params = {
        "dataFinal": data_final,
        "codigoModalidadeContratacao": modalidade,
        "uf": uf,
        "pagina": pagina,
        "tamanhoPagina": TAMANHO_PAGINA,
    }

    espera = ESPERA_INICIAL_RETRY
    ultimo_erro = None

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resp = session.get(BASE_URL, params=params, timeout=60)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as erro:
            ultimo_erro = erro
            print(f"  ⚠ Falha de rede ({type(erro).__name__}). Esperando {espera:.0f}s e tentando de novo "
                  f"({tentativa}/{MAX_TENTATIVAS})...")
            time.sleep(espera)
            espera *= 2
            continue

        if resp.status_code == 429:
            # Respeita o header Retry-After se o servidor mandar; senão usa backoff exponencial
            espera_servidor = resp.headers.get("Retry-After")
            tempo_espera = float(espera_servidor) if espera_servidor else espera
            print(f"  ⚠ Rate limit (429). Esperando {tempo_espera:.0f}s e tentando de novo "
                  f"({tentativa}/{MAX_TENTATIVAS})...")
            time.sleep(tempo_espera)
            espera *= 2  # próxima espera é o dobro, se precisar
            continue

        if resp.status_code >= 500:
            # Erro do próprio servidor do PNCP (instabilidade momentânea) — também vale tentar de novo
            print(f"  ⚠ Erro do servidor ({resp.status_code}). Esperando {espera:.0f}s e tentando de novo "
                  f"({tentativa}/{MAX_TENTATIVAS})...")
            time.sleep(espera)
            espera *= 2
            continue

        if resp.status_code == 204:
            # Sem conteúdo = não há mais resultados para essa consulta
            return {}

        resp.raise_for_status()
        return resp.json()

    raise RuntimeError(
        f"Falha persistente após {MAX_TENTATIVAS} tentativas (UF={uf}, página={pagina}): {ultimo_erro}. "
        "O servidor do PNCP pode estar instável agora — tente rodar de novo em alguns minutos."
    )


def coletar_todas(session: requests.Session) -> dict:
    """Busca todas as páginas, para cada UF e modalidade, deduplicando por numeroControlePNCP."""
    data_final = (date.today() + timedelta(days=JANELA_DIAS)).strftime("%Y%m%d")
    encontradas = {}

    for uf in ESTADOS_PERMITIDOS:
        for modalidade in MODALIDADES:
            print(f"Buscando UF={uf}, modalidade={modalidade}...")
            time.sleep(PAUSA_ENTRE_REQUISICOES)
            pagina = 1
            while True:
                try:
                    data = buscar_pagina(session, uf, modalidade, data_final, pagina)
                except RuntimeError as erro:
                    print(f"  ✗ Desistindo de UF={uf} por agora: {erro}")
                    print(f"    (os resultados já coletados de outros estados não são perdidos)")
                    break

                # A API retorna 204 No Content (corpo vazio) quando não há mais resultados
                if not data:
                    break

                registros = data if isinstance(data, list) else data.get("data", [])
                if not registros:
                    break

                for c in registros:
                    encontradas[c["numeroControlePNCP"]] = c

                total_paginas = data.get("totalPaginas", 1) if isinstance(data, dict) else 1
                print(f"  página {pagina}/{total_paginas} — {len(registros)} itens")

                if pagina >= total_paginas:
                    break
                pagina += 1
                time.sleep(PAUSA_ENTRE_REQUISICOES)

    return encontradas


def passa_filtros(c: dict) -> tuple[bool, list[str]]:
    motivos = []

    texto_completo = normalizar(
        (c.get("objetoCompra") or "") + " " + (c.get("informacaoComplementar") or "")
    )

    # 1. Palavra-chave
    kw_hits = [kw for kw in KEYWORDS if normalizar(kw) in texto_completo]
    if not kw_hits:
        return False, []
    motivos.append("Palavras-chave: " + ", ".join(kw_hits))

    # 2. Valor estimado
    valor = c.get("valorTotalEstimado") or 0
    if valor > VALOR_MAXIMO:
        return False, []
    if valor == 0:
        motivos.append("Valor: não informado")
    else:
        motivos.append(f"Valor: R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # 3. Dedicação exclusiva de mão de obra
    if EXIGIR_DEDICACAO_EXCLUSIVA:
        tem_demo = ("dedicacao exclusiva" in texto_completo) or ("demo" in texto_completo)
        if not tem_demo:
            return False, []
        motivos.append("DEMO: sim")

    # 4. Prazo não pode ser hoje
    if EXCLUIR_PRAZO_HOJE:
        prazo_str = c.get("dataEncerramentoProposta") or c.get("dataAberturaProposta")
        if prazo_str:
            try:
                prazo_data = datetime.fromisoformat(prazo_str).date()
                if prazo_data == date.today():
                    return False, []
            except ValueError:
                pass

    return True, motivos


def calcular_score(c: dict) -> float:
    texto_completo = normalizar((c.get("objetoCompra") or "") + " " + (c.get("informacaoComplementar") or ""))
    kw_hits = sum(1 for kw in KEYWORDS if normalizar(kw) in texto_completo)
    score = kw_hits * 20

    uf = ((c.get("unidadeOrgao") or {}).get("ufSigla") or "").upper()
    if uf == "MA":
        score += 30
    elif uf in ESTADOS_PERMITIDOS:
        score += 15

    valor = c.get("valorTotalEstimado") or 0
    if valor > 0:
        score += min(valor / 1_000_000, 20)

    return score


def dias_ate(data_str: str) -> str:
    if not data_str:
        return "—"
    try:
        d = datetime.fromisoformat(data_str).date()
        delta = (d - date.today()).days
        if delta < 0:
            return f"venceu há {abs(delta)}d"
        if delta == 0:
            return "hoje"
        return f"em {delta}d"
    except ValueError:
        return data_str


def montar_link_edital(c: dict) -> str:
    """Reconstrói a URL pública do edital no site do PNCP a partir do número de controle."""
    orgao = c.get("orgaoEntidade") or {}
    cnpj = orgao.get("cnpj")
    ano = c.get("anoCompra")
    sequencial = c.get("sequencialCompra")
    if cnpj and ano and sequencial:
        return f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}"
    return ""


def gerar_html(itens_filtrados: list[dict], caminho_saida: Path):
    linhas_html = []
    for c, motivos, score in itens_filtrados:
        objeto = (c.get("objetoCompra") or "")[:280]
        orgao_info = c.get("orgaoEntidade") or {}
        orgao = orgao_info.get("razaosocial", "—")
        unidade = c.get("unidadeOrgao") or {}
        cidade = unidade.get("municipioNome", "—")
        estado = unidade.get("ufSigla", "—")
        valor = c.get("valorTotalEstimado") or 0
        valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor else "não informado"
        prazo = c.get("dataEncerramentoProposta") or c.get("dataAberturaProposta")
        prazo_fmt = dias_ate(prazo)
        link_edital = montar_link_edital(c)
        modalidade = c.get("modalidadeNome", "—")
        numero_controle = c.get("numeroControlePNCP", "—")

        linhas_html.append(f"""
        <div class="card">
          <div class="card-header">
            <span class="score">{score:.0f} pts</span>
            <span class="tag">{modalidade}</span>
            <span class="uf">{estado}</span>
          </div>
          <h3>{orgao}</h3>
          <p class="objeto">{objeto}{'...' if len(c.get('objetoCompra','') or '') > 280 else ''}</p>
          <div class="meta">
            <span>📍 {cidade}/{estado}</span>
            <span>💰 {valor_fmt}</span>
            <span>⏰ Proposta encerra: {prazo_fmt}</span>
            <span>🔖 {numero_controle}</span>
          </div>
          <div class="motivos">{" · ".join(motivos)}</div>
          {f'<a href="{link_edital}" target="_blank" class="link">Ver edital no PNCP →</a>' if link_edital else ''}
        </div>
        """)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Licitações filtradas - PNCP</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #f4f5f7; margin: 0; padding: 24px; color: #1a1a1a; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .subtitle {{ color: #666; margin-bottom: 24px; font-size: 14px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }}
  .card {{ background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-left: 4px solid #16a34a; }}
  .card-header {{ display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }}
  .score {{ background: #16a34a; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  .tag {{ background: #eee; padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
  .uf {{ margin-left: auto; font-weight: 700; color: #444; }}
  h3 {{ margin: 4px 0; font-size: 15px; }}
  .objeto {{ font-size: 13px; color: #333; line-height: 1.4; }}
  .meta {{ display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: #555; margin-top: 8px; }}
  .motivos {{ font-size: 11px; color: #888; margin-top: 8px; border-top: 1px solid #eee; padding-top: 6px; }}
  .link {{ display: inline-block; margin-top: 10px; font-size: 13px; color: #16a34a; text-decoration: none; font-weight: 600; }}
  .link:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
  <h1>🎯 Licitações filtradas — Fonte: PNCP (oficial)</h1>
  <div class="subtitle">
    {len(itens_filtrados)} licitações encontradas · gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}
  </div>
  <div class="grid">
    {"".join(linhas_html)}
  </div>
</body>
</html>"""

    caminho_saida.write_text(html, encoding="utf-8")


def gerar_html_do_banco(licitacoes: list[dict], caminho_saida: Path):
    """Mesmo dashboard de antes, mas lendo do banco (já com histórico e marca de 'nova')."""
    import db as db_module

    linhas_html = []
    for lic in licitacoes:
        objeto = (lic.get("objeto") or "")[:280]
        motivos = json.loads(lic.get("motivos") or "[]")
        prazo_fmt = dias_ate(lic.get("data_encerramento_proposta") or lic.get("data_abertura_proposta"))
        valor = lic.get("valor_estimado") or 0
        valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor else "não informado"
        tag_nova = '<span class="tag nova">🆕 NOVA</span>' if db_module.eh_nova(lic) else ""

        linhas_html.append(f"""
        <div class="card">
          <div class="card-header">
            <span class="score">{lic.get('score', 0):.0f} pts</span>
            {tag_nova}
            <span class="tag">{lic.get('modalidade', '—')}</span>
            <span class="uf">{lic.get('uf', '—')}</span>
          </div>
          <h3>{lic.get('orgao', '—')}</h3>
          <p class="objeto">{objeto}{'...' if len(lic.get('objeto','') or '') > 280 else ''}</p>
          <div class="meta">
            <span>📍 {lic.get('cidade', '—')}/{lic.get('uf', '—')}</span>
            <span>💰 {valor_fmt}</span>
            <span>⏰ Proposta encerra: {prazo_fmt}</span>
            <span>🔖 {lic.get('numero_controle', '—')}</span>
          </div>
          <div class="motivos">{" · ".join(motivos)}</div>
          {f'<a href="{lic.get("link_edital")}" target="_blank" class="link">Ver edital no PNCP →</a>' if lic.get('link_edital') else ''}
        </div>
        """)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Licitações filtradas - PNCP</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #f4f5f7; margin: 0; padding: 24px; color: #1a1a1a; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .subtitle {{ color: #666; margin-bottom: 24px; font-size: 14px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }}
  .card {{ background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-left: 4px solid #16a34a; }}
  .card-header {{ display: flex; gap: 8px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }}
  .score {{ background: #16a34a; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  .tag {{ background: #eee; padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
  .tag.nova {{ background: #fef3c7; color: #92400e; font-weight: 700; }}
  .uf {{ margin-left: auto; font-weight: 700; color: #444; }}
  h3 {{ margin: 4px 0; font-size: 15px; }}
  .objeto {{ font-size: 13px; color: #333; line-height: 1.4; }}
  .meta {{ display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: #555; margin-top: 8px; }}
  .motivos {{ font-size: 11px; color: #888; margin-top: 8px; border-top: 1px solid #eee; padding-top: 6px; }}
  .link {{ display: inline-block; margin-top: 10px; font-size: 13px; color: #16a34a; text-decoration: none; font-weight: 600; }}
  .link:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
  <h1>🎯 Licitações filtradas — Fonte: PNCP (oficial)</h1>
  <div class="subtitle">
    {len(licitacoes)} licitações ativas no histórico · gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}
  </div>
  <div class="grid">
    {"".join(linhas_html)}
  </div>
</body>
</html>"""

    caminho_saida.write_text(html, encoding="utf-8")


def main():
    import db as db_module

    db_module.inicializar_db()

    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    })

    todas = coletar_todas(session)
    print(f"\nTotal de contratações únicas encontradas (antes dos filtros): {len(todas)}")

    aprovadas = []
    for c in todas.values():
        ok, motivos = passa_filtros(c)
        if ok:
            score = calcular_score(c)
            aprovadas.append((c, motivos, score))

    aprovadas.sort(key=lambda x: x[2], reverse=True)
    print(f"Licitações que passaram nos filtros nesta rodada: {len(aprovadas)}")

    resumo = db_module.salvar_resultado_da_rodada(aprovadas)
    print(f"Novas desde a última rodada: {resumo['novas_nesta_rodada']}")
    print(f"Total ativas no banco agora: {resumo['total_ativas']}")

    licitacoes_ativas = db_module.listar_ativas()
    saida = Path(__file__).parent / "licitacoes.html"
    gerar_html_do_banco(licitacoes_ativas, saida)
    print(f"\nDashboard gerado em: {saida.resolve()}")
    print(f"Banco de dados em: {db_module.CAMINHO_DB.resolve()}")


if __name__ == "__main__":
    main()