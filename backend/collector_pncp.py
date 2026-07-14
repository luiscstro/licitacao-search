import time
from datetime import date, timedelta

import requests
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app import models

ESTADOS_COBERTOS = ["MA", "PI", "PA", "TO", "CE"]

MODALIDADES = [6]  
JANELA_DIAS = 60
BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
TAMANHO_PAGINA = 50
PAUSA_ENTRE_REQUISICOES = 1.0
MAX_TENTATIVAS = 6
ESPERA_INICIAL_RETRY = 5

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
            print(f"  ⚠ Falha de rede. Esperando {espera:.0f}s ({tentativa}/{MAX_TENTATIVAS})...")
            time.sleep(espera)
            espera *= 2
            continue

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

    raise RuntimeError(f"Falha persistente (UF={uf}, página={pagina}): {ultimo_erro}")


def coletar_todas(session: requests.Session) -> dict:
    data_final = (date.today() + timedelta(days=JANELA_DIAS)).strftime("%Y%m%d")
    encontradas = {}

    for uf in ESTADOS_COBERTOS:
        for modalidade in MODALIDADES:
            print(f"Buscando UF={uf}, modalidade={modalidade}...")
            time.sleep(PAUSA_ENTRE_REQUISICOES)
            pagina = 1
            while True:
                try:
                    data = buscar_pagina(session, uf, modalidade, data_final, pagina)
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
                print(f"  página {pagina}/{total_paginas} — {len(registros)} itens")
                if pagina >= total_paginas:
                    break
                pagina += 1
                time.sleep(PAUSA_ENTRE_REQUISICOES)

    return encontradas


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

        existente = db.query(models.Licitacao).filter(
            models.Licitacao.numero_controle == numero_controle
        ).first()

        if existente:
            existente.orgao = orgao_info.get("razaosocial", "—")
            existente.cidade = unidade.get("municipioNome", "—")
            existente.uf = unidade.get("ufSigla", "—")
            existente.objeto = c.get("objetoCompra", "")
            existente.informacao_complementar = c.get("informacaoComplementar", "") or ""
            existente.valor_estimado = c.get("valorTotalEstimado") or 0
            existente.modalidade = c.get("modalidadeNome", "—")
            existente.data_abertura_proposta = c.get("dataAberturaProposta")
            existente.data_encerramento_proposta = c.get("dataEncerramentoProposta")
            existente.link_edital = link
            existente.ultima_vez_vista = agora
            existente.ativa = True
        else:
            db.add(models.Licitacao(
                numero_controle=numero_controle,
                orgao=orgao_info.get("razaosocial", "—"),
                cidade=unidade.get("municipioNome", "—"),
                uf=unidade.get("ufSigla", "—"),
                objeto=c.get("objetoCompra", ""),
                informacao_complementar=c.get("informacaoComplementar", "") or "",
                valor_estimado=c.get("valorTotalEstimado") or 0,
                modalidade=c.get("modalidadeNome", "—"),
                data_abertura_proposta=c.get("dataAberturaProposta"),
                data_encerramento_proposta=c.get("dataEncerramentoProposta"),
                link_edital=link,
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

    todas = coletar_todas(session)
    print(f"\nTotal de contratações únicas encontradas: {len(todas)}")

    db = SessionLocal()
    try:
        sincronizar_com_banco(db, todas)
    finally:
        db.close()

    print("Base compartilhada de licitações atualizada com sucesso.")


if __name__ == "__main__":
    main()
