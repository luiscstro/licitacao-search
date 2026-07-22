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

import sys
import time
from datetime import date, timedelta

import requests
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app import models
from app.scoring import montar_texto_busca, montar_texto_busca_objeto

# No Windows, quando a saída é redirecionada pra um arquivo (ex: "> log.txt"),
# duas coisas dão problema:
# 1. O Python às vezes tenta usar uma codificação antiga (cp1252) que não
#    sabe escrever emojis (⚠, ✗, etc) — e quebra o script no meio.
# 2. Por padrão, a saída redirecionada fica "em buffer" (só escreve no
#    arquivo de vez em quando, em blocos) — então o arquivo de log fica
#    vazio por um tempo bem longo mesmo com o script rodando normalmente.
# As duas linhas abaixo resolvem os dois problemas: força UTF-8 (com
# "errors=replace" pra NUNCA travar por causa de um caractere raro) e
# força escrever cada linha imediatamente (line_buffering=True).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

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
    # 4: "Concorrência - Eletrônica",   # desativado por ora: volume alto, menos relevante pra serviços
    # 5: "Concorrência - Presencial",   # desativado por ora: idem
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    10: "Manifestação de Interesse",
    12: "Credenciamento",              # geralmente aparece como "Chamamento Público" na prática
    # 9: "Inexigibilidade",            # desativado por ora: raro pro seu tipo de negócio
    # 11: "Pré-qualificação",          # desativado por ora: raro
    # 13: "Leilão - Presencial",
}
# Pra reativar alguma, é só remover o "#" da linha correspondente e rodar de novo.

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
    encontradas_brasil = {}
    falhou_no_meio = False

    if BUSCAR_BRASIL_INTEIRO:
        print(f"Buscando {rotulo}, Brasil inteiro...")
        pagina = 1
        try:
            while True:
                data = buscar_pagina(session, codigo_modalidade, data_final, pagina, None)
                if not data:
                    break
                registros = data if isinstance(data, list) else data.get("data", [])
                if not registros:
                    break
                for c in registros:
                    encontradas_brasil[c["numeroControlePNCP"]] = c
                total_paginas = data.get("totalPaginas", 1) if isinstance(data, dict) else 1
                print(f"  página {pagina}/{total_paginas} — {len(registros)} itens")
                if pagina >= total_paginas:
                    break
                pagina += 1
                time.sleep(PAUSA_ENTRE_REQUISICOES)
            return encontradas_brasil
        except ErroRequisicaoInvalida:
            print(f"  ↳ Brasil inteiro não é aceito pra {rotulo}. Buscando estado por estado em vez disso...")
        except RuntimeError as erro:
            print(f"  ⚠ {rotulo} falhou no meio da coleta nacional (parou na página {pagina}, "
                  f"{len(encontradas_brasil)} itens coletados até aqui): {erro}")
            print(f"  ↳ Isso deixaria dados incompletos — caindo pra busca estado por estado "
                  f"pra completar o que faltou, em vez de aceitar um resultado parcial.")
            falhou_no_meio = True

    # Fallback: estado por estado (ou comportamento padrão se
    # BUSCAR_BRASIL_INTEIRO = False)
    estados = TODOS_OS_ESTADOS if BUSCAR_BRASIL_INTEIRO else ESTADOS_COBERTOS

    if falhou_no_meio:
        # Já sabemos que não é erro de parâmetro (chegou a coletar páginas
        # de verdade) — é instabilidade/rate limit. Não faz sentido testar
        # "1 estado primeiro"; já vamos direto pra todos, aproveitando o
        # que já tinha sido coletado antes de falhar.
        encontradas = dict(encontradas_brasil)
        for uf in estados:
            print(f"Buscando {rotulo}, UF={uf}...")
            try:
                parciais = _coletar_por_uf(session, codigo_modalidade, data_final, uf)
            except ErroRequisicaoInvalida as erro:
                print(f"  ✗ UF={uf} rejeitado: {erro}. Pulando pra o próximo estado.")
                parciais = {}
            encontradas.update(parciais)
            time.sleep(PAUSA_ENTRE_REQUISICOES)
        print(f"  -> Recuperação completa: {len(encontradas)} itens ao todo (incluindo os {len(encontradas_brasil)} de antes da falha)")
        return encontradas

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


def salvar_licitacoes(db: Session, contratacoes: dict):
    """Grava/atualiza um lote de licitações no banco e já comita — chamado
    UMA VEZ POR MODALIDADE, assim que ela termina de ser coletada. Isso é
    o que garante que, mesmo se o script cair no meio (erro inesperado,
    falta de luz, etc), o que já foi coletado com sucesso não se perde."""
    from datetime import datetime
    agora = datetime.utcnow()

    for numero_controle, c in contratacoes.items():
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
        texto_busca_objeto = montar_texto_busca_objeto(objeto, info_complementar)

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
            existente.texto_busca_objeto = texto_busca_objeto
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
                texto_busca_objeto=texto_busca_objeto,
                primeira_vez_vista=agora,
                ultima_vez_vista=agora,
                ativa=True,
            ))

    db.commit()


def marcar_inativas(db: Session, todos_ids_vistos: set):
    """Chamado UMA VEZ, depois que TODAS as modalidades foram coletadas e
    salvas. Marca como inativa qualquer licitação que estava ativa no banco
    mas não apareceu em nenhuma modalidade coletada dessa vez (prazo
    encerrado, retirada, etc)."""
    todas_ativas = db.query(models.Licitacao).filter(models.Licitacao.ativa == True).all()  # noqa: E712
    marcadas = 0
    for lic in todas_ativas:
        if lic.numero_controle not in todos_ids_vistos:
            lic.ativa = False
            marcadas += 1
    db.commit()
    return marcadas


def main():
    Base.metadata.create_all(bind=engine)

    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    })

    data_final = (date.today() + timedelta(days=JANELA_DIAS)).strftime("%Y%m%d")
    db = SessionLocal()
    todos_ids_vistos = set()
    inicio = time.time()

    try:
        for codigo, nome in MODALIDADES.items():
            try:
                parciais = coletar_modalidade(session, codigo, nome, data_final)
            except Exception as erro:  # não deixa uma modalidade travar as outras
                print(f"  ✗ Erro inesperado em modalidade={nome}: {erro}")
                parciais = {}

            # Salva JÁ, assim que essa modalidade termina — não espera as
            # outras. Se o script cair depois disso, o que já foi salvo
            # continua salvo.
            salvar_licitacoes(db, parciais)
            todos_ids_vistos.update(parciais.keys())
            print(f"  -> {nome}: {len(parciais)} itens salvos (acumulado: {len(todos_ids_vistos)})\n")

        duracao_min = (time.time() - inicio) / 60
        print(f"\nTotal de contratações únicas coletadas: {len(todos_ids_vistos)} (em {duracao_min:.1f} minutos)")

        marcadas = marcar_inativas(db, todos_ids_vistos)
        print(f"Licitações marcadas como inativas (sumiram desde a última coleta): {marcadas}")
        print("Base compartilhada de licitações atualizada com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    main()