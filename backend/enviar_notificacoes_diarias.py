#!/usr/bin/env python3
"""
Envia o resumo diário de licitações novas por e-mail — uma execução por dia,
depois do coletor (`collector_pncp.py`) já ter rodado.

Pra cada Empresa com critérios ativos, procura licitações que:
  - estão ativas
  - foram vistas pela primeira vez nas últimas ~26h (janela um pouco maior
    que 24h pra cobrir folga no agendamento, sem precisar de uma tabela de
    "já notificado" separada)
  - batem com pelo menos um critério ativo da empresa

E manda um e-mail de resumo pra cada usuário da empresa com
`receber_notificacoes=True`.

Configuração necessária (variáveis de ambiente — ver app/email_utils.py):
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

Como usar:
    cd backend
    python3 enviar_notificacoes_diarias.py
"""

import sys
from datetime import datetime, timedelta

from app import email_utils, models, scoring
from app.database import SessionLocal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

JANELA_HORAS = 26


def montar_itens_para_empresa(db, empresa: models.Empresa, desde: datetime) -> list[dict]:
    criterios = (
        db.query(models.Criterio)
        .filter(
            models.Criterio.empresa_id == empresa.id,
            models.Criterio.ativo == True,  # noqa: E712
        )
        .all()
    )
    if not criterios:
        return []

    candidatas = (
        db.query(models.Licitacao)
        .filter(
            models.Licitacao.ativa == True,  # noqa: E712
            models.Licitacao.primeira_vez_vista >= desde,
        )
        .all()
    )

    itens = []
    for licitacao in candidatas:
        melhor_score, melhores_motivos, melhor_criterio = -1, [], None
        for criterio in criterios:
            passou, motivos, score = scoring.aplicar_criterio(licitacao, criterio)
            if passou and score > melhor_score:
                melhor_score, melhores_motivos, melhor_criterio = score, motivos, criterio

        if melhor_criterio is not None:
            itens.append(
                {
                    "orgao": licitacao.orgao,
                    "cidade": licitacao.cidade,
                    "uf": licitacao.uf,
                    "valor_estimado": licitacao.valor_estimado,
                    "objeto": licitacao.objeto,
                    "modalidade": licitacao.modalidade,
                    "data_encerramento_proposta": licitacao.data_encerramento_proposta,
                    "link_edital": licitacao.link_edital,
                    "motivos": melhores_motivos,
                    "criterio_nome": melhor_criterio.nome,
                }
            )

    itens.sort(key=lambda i: i["valor_estimado"] or 0, reverse=True)
    return itens


def main():
    if not email_utils.smtp_configurado():
        print("SMTP não configurado (SMTP_HOST/SMTP_USER/SMTP_PASSWORD) — nada a fazer.")
        return

    desde = datetime.utcnow() - timedelta(hours=JANELA_HORAS)
    db = SessionLocal()
    total_emails, total_erros = 0, 0

    try:
        empresas = db.query(models.Empresa).all()
        print(
            f"[{datetime.now()}] Verificando {len(empresas)} empresa(s), licitações vistas desde {desde}..."
        )

        for empresa in empresas:
            itens = montar_itens_para_empresa(db, empresa, desde)
            if not itens:
                continue

            usuarios = (
                db.query(models.User)
                .filter(
                    models.User.empresa_id == empresa.id,
                    models.User.ativo == True,  # noqa: E712
                    models.User.receber_notificacoes == True,  # noqa: E712
                )
                .all()
            )
            if not usuarios:
                continue

            corpo_html = email_utils.montar_email_resumo(empresa.nome, itens)
            assunto = f"LicitTracker — {len(itens)} nova(s) licitação(ões) para {empresa.nome}"

            for usuario in usuarios:
                try:
                    email_utils.enviar_email(usuario.email, assunto, corpo_html)
                    total_emails += 1
                    print(f"  ✓ enviado para {usuario.email} ({len(itens)} itens, empresa '{empresa.nome}')")
                except Exception as erro:
                    total_erros += 1
                    print(f"  ✗ falhou para {usuario.email}: {erro}")
    finally:
        db.close()

    print(f"[{datetime.now()}] Concluído — {total_emails} e-mail(s) enviado(s), {total_erros} erro(s).")


if __name__ == "__main__":
    main()
