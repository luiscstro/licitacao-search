#!/usr/bin/env python3
"""
Envia alertas por e-mail de documentos/certidões próximos do vencimento —
uma execução por dia, junto com o resumo diário de licitações.

Pra cada DocumentoHabilitacao com data_validade preenchida, calcula quantos
dias faltam e acha o maior limiar em [30, 15, 7, 1, 0] já cruzado. Só
dispara e-mail (e atualiza `ultimo_alerta_dias`) se esse limiar for
diferente do último já notificado — evita alerta duplicado todo dia sem
precisar de uma tabela de log separada.

Configuração necessária (variáveis de ambiente — ver app/email_utils.py):
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

Como usar:
    cd backend
    python3 enviar_alertas_documentos.py
"""

import sys
from datetime import datetime

from app.database import SessionLocal
from app import models, email_utils

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def limiar_cruzado(dias_restantes: int) -> int | None:
    """Acha o maior limiar em LIMIARES_ALERTA_VENCIMENTO que já foi
    cruzado (dias_restantes <= limiar). None se nenhum foi cruzado ainda."""
    limiares_cruzados = [l for l in models.LIMIARES_ALERTA_VENCIMENTO if dias_restantes <= l]
    return max(limiares_cruzados) if limiares_cruzados else None


def montar_itens_para_empresa(db, empresa: models.Empresa) -> tuple[list[dict], list[models.DocumentoHabilitacao]]:
    documentos = db.query(models.DocumentoHabilitacao).filter(
        models.DocumentoHabilitacao.empresa_id == empresa.id,
        models.DocumentoHabilitacao.data_validade.isnot(None),
    ).all()

    itens, documentos_a_marcar = [], []
    hoje = datetime.utcnow()

    for documento in documentos:
        dias_restantes = (documento.data_validade - hoje).days
        limiar = limiar_cruzado(dias_restantes)
        if limiar is None:
            continue
        if documento.ultimo_alerta_dias is not None and limiar >= documento.ultimo_alerta_dias:
            continue  # já notificou esse limiar (ou um mais cedo) antes

        itens.append({
            "nome": documento.nome,
            "categoria": documento.categoria,
            "dias_restantes": dias_restantes,
        })
        documento.ultimo_alerta_dias = limiar
        documentos_a_marcar.append(documento)

    itens.sort(key=lambda i: i["dias_restantes"])
    return itens, documentos_a_marcar


def main():
    if not email_utils.smtp_configurado():
        print("SMTP não configurado (SMTP_HOST/SMTP_USER/SMTP_PASSWORD) — nada a fazer.")
        return

    db = SessionLocal()
    total_emails, total_erros = 0, 0

    try:
        empresas = db.query(models.Empresa).all()
        print(f"[{datetime.now()}] Verificando documentos de {len(empresas)} empresa(s)...")

        for empresa in empresas:
            itens, documentos_a_marcar = montar_itens_para_empresa(db, empresa)
            if not itens:
                continue

            usuarios = db.query(models.User).filter(
                models.User.empresa_id == empresa.id,
                models.User.ativo == True,  # noqa: E712
                models.User.receber_notificacoes == True,  # noqa: E712
            ).all()

            if not usuarios:
                db.commit()  # ainda assim marca os limiares, pra não reprocessar todo dia
                continue

            corpo_html = email_utils.montar_email_alerta_vencimento(empresa.nome, itens)
            assunto = f"LicitTracker — {len(itens)} documento(s) próximo(s) do vencimento em {empresa.nome}"

            for usuario in usuarios:
                try:
                    email_utils.enviar_email(usuario.email, assunto, corpo_html)
                    total_emails += 1
                    print(f"  ✓ enviado para {usuario.email} ({len(itens)} itens, empresa '{empresa.nome}')")
                except Exception as erro:
                    total_erros += 1
                    print(f"  ✗ falhou para {usuario.email}: {erro}")

            db.commit()
    finally:
        db.close()

    print(f"[{datetime.now()}] Concluído — {total_emails} e-mail(s) enviado(s), {total_erros} erro(s).")


if __name__ == "__main__":
    main()
