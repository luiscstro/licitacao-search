#!/usr/bin/env python3
"""
Coletor de licitações do PNCP — versão nacional, multi-modalidade.

Esse coletor NÃO aplica os filtros de nenhum cliente específico. Ele baixa
os dados do PNCP e guarda TUDO numa base compartilhada (tabela
`licitacoes`). Quem filtra por critério é a API, na hora que cada cliente
consulta — e a busca livre (sem critério) enxerga essa base inteira,
Brasil todo, qualquer modalidade coletada.

IMPORTANTE sobre volume/tempo: coletar o Brasil inteiro em várias
modalidades é MUITO mais pesado que os 5 estados de antes. O PNCP tem
limite de requisições (rate limit) e às vezes fica instável — o script já
tem retry automático pra isso, mas a primeira execução pode demorar bem
mais que as anteriores. Rodar de madrugada (via agendamento) ajuda.

Como usar:
    cd backend
    python3 collector_pncp.py
"""

import time
from datetime import date, timedelta

import requests
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app import models
from app.scoring import montar_texto_busca

# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Códigos de modalidade do PNCP (tabela oficial de domínio).
# Comentados os que normalmente não interessam pra serviços/compras
# (Leilão, Concurso, Diálogo Competitivo) — descomente se quiser incluir.
MODALIDADES = {
    # 1: "Leilão - Eletrônico",
    # 2: "Diálogo Competitivo",
    # 3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    # 13: "Leilão - Presencial",
}

# Se True, busca o Brasil inteiro numa passada só por modalidade (mais
# rápido — menos requisições). Se False, faz um loop por UF (mais lento,
# mas útil se você quiser reduzir escopo geográfico de novo no futuro).
BUSCAR_BRASIL_INTEIRO = True
ESTADOS_COBERTOS = ["MA", "PI", "PA", "TO", "CE"]  # só usado se BUSCAR_BRASIL_INTEIRO = False

JANELA_DIAS = 60
BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
TAMANHO_PAGINA = 50  # esse endpoint específico rejeita valores maiores (testado: 100 dá "Tamanho de página inválido")
PAUSA_ENTRE_REQUISICOES = 1.0
MAX_TENTATIVAS = 6
ESPERA_INICIAL_RETRY = 5

# ============================================================


class ErroRequisicaoInvalida(Exception):
    """Erro 400 — a combinação de parâmetros foi rejeitada pelo PNCP.
    Diferente de RuntimeError (falha de rede/instabilidade), esse erro
    não adianta tentar de novo do mesmo jeito — precisa mudar a estratégia."""
    pass


def buscar_pagina(session: requests.Session, modalidade: int, data_final: str, pagina: int, uf: str | None) -> dict:
    params = {
        "dataFinal": data_final,
        "codigoModalidadeContratacao": modalidade,
        "pagina": pagina,
        "tamanhoPagina": TAMANHO_PAGINA,
    }
    if uf:
        params["uf"] = uf

    espera = ESPERA_INICIAL_RETRY
    ultimo_erro = None

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resp = session.get(BASE_URL, params=params, timeout=90)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as erro:
            ultimo_erro = erro
            print(f"  ⚠ Falha de rede. Esperando {espera:.0f}s ({tentativa}/{MAX_TENTATIVAS})...")
            time.sleep(espera)
            espera *= 2
            continue

        if resp.status_code == 400:
            # Erro do CLIENTE (parâmetros rejeitados) — tentar de novo do
            # mesmo jeito não resolve. Mostra o motivo e desiste dessa combinação.
            print(f"  ✗ Requisição rejeitada (400) pra modalidade={modalidade}, uf={uf or 'BRASIL'}: {resp.text[:300]}")
            raise ErroRequisicaoInvalida(resp.text)

        if resp.status_code == 429:
            espera_servidor = resp.headers.get("Retry-After")
            tempo_espera = float(espera_servidor) if espera_servidor else espera
            print(f"  ⚠ Rate limit. Esperando {tempo_espera:.0f}s ({tentativa}/{MAX_TENTATIVAS})...")
            time.sleep(tempo_espera)
            espera *= 2
            continue

        if resp.status_code >= 500:
            print(f"  ⚠ Erro do servidor ({resp.status_code}). Esperando {espera:.0f}s...")
            time.sleep(espera)
            espera *= 2
            continue

        if resp.status_code == 204:
            return {}

        resp.raise_for_status()
        return resp.json()

    raise RuntimeError(f"Falha persistente (modalidade={modalidade}, página={pagina}): {ultimo_erro}")


def _coletar_por_uf(session: requests.Session, codigo_modalidade: int, data_final: str, uf: str) -> dict:
    """Coleta todas as páginas de uma modalidade, pra um único estado.
    Erro de parâmetro inválido (400) NÃO é engolido aqui — propaga pra quem
    chamou decidir o que fazer (pode ser um problema sistemático, não
    específico desse estado)."""
    encontradas = {}
    pagina = 1
    while True:
        try:
            data = buscar_pagina(session, codigo_modalidade, data_final, pagina, uf)
        except RuntimeError as erro:
            print(f"  ✗ Desistindo de UF={uf}: {erro}")
            break

        if not data:
            break
        registros = data if isinstance(data, list) else data.get("data", [])
        if not registros:
            break

        for c in registros:
            encontradas[c["numeroControlePNCP"]] = c

        total_paginas = data.get("totalPaginas", 1) if isinstance(data, dict) else 1
        print(f"  [{uf}] página {pagina}/{total_paginas} — {len(registros)} itens")
        if pagina >= total_paginas:
            break
        pagina += 1
        time.sleep(PAUSA_ENTRE_REQUISICOES)

    return encontradas


# Todos os estados + DF — usado como fallback quando a consulta nacional
# (sem uf) é rejeitada pelo PNCP para alguma modalidade específica.
TODOS_OS_ESTADOS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
]


def coletar_modalidade(session: requests.Session, codigo_modalidade: int, nome_modalidade: str, data_final: str) -> dict:
    """Tenta coletar Brasil inteiro numa passada só (mais rápido). Se o
    PNCP rejeitar essa combinação pra essa modalidade específica (erro 400),
    cai automaticamente para buscar estado por estado, sem travar o resto
    da coleta."""
    rotulo = f"modalidade={nome_modalidade} ({codigo_modalidade})"

    if BUSCAR_BRASIL_INTEIRO:
        print(f"Buscando {rotulo}, Brasil inteiro...")
        pagina = 1
        encontradas = {}
        try:
            while True:
                data = buscar_pagina(session, codigo_modalidade, data_final, pagina, None)
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
        except ErroRequisicaoInvalida:
            print(f"  ↳ Brasil inteiro não é aceito pra {rotulo}. Buscando estado por estado em vez disso...")
        except RuntimeError as erro:
            print(f"  ✗ Desistindo de {rotulo} (Brasil inteiro): {erro}")
            return encontradas

    # Fallback: estado por estado (ou comportamento padrão se
    # BUSCAR_BRASIL_INTEIRO = False)
    estados = TODOS_OS_ESTADOS if BUSCAR_BRASIL_INTEIRO else ESTADOS_COBERTOS

    # Teste rápido: se o primeiro estado também for rejeitado com o mesmo
    # tipo de erro, o problema provavelmente não é sobre UF/Brasil-inteiro
    # (pode ser outro parâmetro, tipo tamanho de página) — desiste da
    # modalidade inteira em vez de repetir o erro em mais 26 estados à toa.
    try:
        primeiro_resultado = _coletar_por_uf(session, codigo_modalidade, data_final, estados[0])
    except ErroRequisicaoInvalida as erro:
        print(f"  ✗ {rotulo} também falhou no primeiro estado testado ({estados[0]}) com o mesmo tipo de erro.")
        print(f"    Provavelmente não é um problema de UF — desistindo dessa modalidade. Detalhe: {erro}")
        return {}

    encontradas = dict(primeiro_resultado)
    for uf in estados[1:]:
        print(f"Buscando {rotulo}, UF={uf}...")
        try:
            parciais = _coletar_por_uf(session, codigo_modalidade, data_final, uf)
        except ErroRequisicaoInvalida as erro:
            print(f"  ✗ UF={uf} rejeitado: {erro}. Pulando pra o próximo estado.")
            parciais = {}
        encontradas.update(parciais)
        time.sleep(PAUSA_ENTRE_REQUISICOES)
    return encontradas


def coletar_todas(session: requests.Session) -> dict:
    data_final = (date.today() + timedelta(days=JANELA_DIAS)).strftime("%Y%m%d")
    todas = {}
    for codigo, nome in MODALIDADES.items():
        try:
            parciais = coletar_modalidade(session, codigo, nome, data_final)
        except Exception as erro:  # não deixa uma modalidade travar as outras
            print(f"  ✗ Erro inesperado em modalidade={nome}: {erro}")
            parciais = {}
        todas.update(parciais)
        print(f"  -> {nome}: {len(parciais)} itens (acumulado: {len(todas)})\n")
    return todas


def sincronizar_com_banco(db: Session, contratacoes: dict):
    from datetime import datetime
    agora = datetime.utcnow()
    ids_vistos = set()

    for numero_controle, c in contratacoes.items():
        ids_vistos.add(numero_controle)
        orgao_info = c.get("orgaoEntidade") or {}
        unidade = c.get("unidadeOrgao") or {}
        cnpj = orgao_info.get("cnpj")
        ano = c.get("anoCompra")
        sequencial = c.get("sequencialCompra")
        link = f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}" if cnpj and ano and sequencial else ""

        objeto = c.get("objetoCompra", "")
        orgao_nome = orgao_info.get("razaosocial", "—")
        cidade = unidade.get("municipioNome", "—")
        info_complementar = c.get("informacaoComplementar", "") or ""
        texto_busca = montar_texto_busca(objeto, orgao_nome, cidade, info_complementar)

        existente = db.query(models.Licitacao).filter(
            models.Licitacao.numero_controle == numero_controle
        ).first()

        if existente:
            existente.orgao = orgao_nome
            existente.cidade = cidade
            existente.uf = unidade.get("ufSigla", "—")
            existente.objeto = objeto
            existente.informacao_complementar = info_complementar
            existente.valor_estimado = c.get("valorTotalEstimado") or 0
            existente.modalidade = c.get("modalidadeNome", "—")
            existente.data_abertura_proposta = c.get("dataAberturaProposta")
            existente.data_encerramento_proposta = c.get("dataEncerramentoProposta")
            existente.link_edital = link
            existente.texto_busca = texto_busca
            existente.ultima_vez_vista = agora
            existente.ativa = True
        else:
            db.add(models.Licitacao(
                numero_controle=numero_controle,
                orgao=orgao_nome,
                cidade=cidade,
                uf=unidade.get("ufSigla", "—"),
                objeto=objeto,
                informacao_complementar=info_complementar,
                valor_estimado=c.get("valorTotalEstimado") or 0,
                modalidade=c.get("modalidadeNome", "—"),
                data_abertura_proposta=c.get("dataAberturaProposta"),
                data_encerramento_proposta=c.get("dataEncerramentoProposta"),
                link_edital=link,
                texto_busca=texto_busca,
                primeira_vez_vista=agora,
                ultima_vez_vista=agora,
                ativa=True,
            ))

    todas_ativas = db.query(models.Licitacao).filter(models.Licitacao.ativa == True).all()  # noqa: E712
    for lic in todas_ativas:
        if lic.numero_controle not in ids_vistos:
            lic.ativa = False

    db.commit()


def main():
    Base.metadata.create_all(bind=engine)

    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    })

    inicio = time.time()
    todas = coletar_todas(session)
    duracao_min = (time.time() - inicio) / 60
    print(f"\nTotal de contratações únicas encontradas: {len(todas)} (em {duracao_min:.1f} minutos)")

    db = SessionLocal()
    try:
        sincronizar_com_banco(db, todas)
    finally:
        db.close()

    print("Base compartilhada de licitações atualizada com sucesso.")


if __name__ == "__main__":
    main()