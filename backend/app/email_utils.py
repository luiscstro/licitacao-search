"""
Envio de e-mail (resumo diário de licitações novas) via SMTP simples.

Configuração por variável de ambiente — mesmo padrão já usado pra
SECRET_KEY em auth.py:
    SMTP_HOST      ex: smtp.gmail.com
    SMTP_PORT      ex: 587 (default)
    SMTP_USER      ex: seuemail@gmail.com
    SMTP_PASSWORD  senha de app (NÃO a senha normal da conta, se tiver 2FA)
    SMTP_FROM      opcional — usa SMTP_USER se não for definida
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


def smtp_configurado() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def enviar_email(destinatario: str, assunto: str, corpo_html: str) -> None:
    """Manda um e-mail HTML simples. Lança exceção se o SMTP não estiver
    configurado ou se o envio falhar — quem chama decide como tratar/logar."""
    if not smtp_configurado():
        raise RuntimeError(
            "SMTP não configurado — defina SMTP_HOST, SMTP_USER e SMTP_PASSWORD "
            "como variáveis de ambiente antes de rodar o envio de notificações."
        )

    mensagem = MIMEMultipart("alternative")
    mensagem["Subject"] = assunto
    mensagem["From"] = SMTP_FROM
    mensagem["To"] = destinatario
    mensagem.attach(MIMEText(corpo_html, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as servidor:
        servidor.starttls()
        servidor.login(SMTP_USER, SMTP_PASSWORD)
        servidor.sendmail(SMTP_FROM, [destinatario], mensagem.as_string())


def _formatar_valor(valor: float) -> str:
    return f"R$ {valor or 0:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_email_resumo(empresa_nome: str, itens: list[dict]) -> str:
    """Monta o HTML do resumo diário. Cada item de `itens` é um dict com:
    orgao, cidade, uf, valor_estimado, objeto, modalidade,
    data_encerramento_proposta, link_edital, motivos (lista de str),
    criterio_nome."""
    linhas_html = []
    for item in itens:
        motivos_html = "".join(f"<li>{m}</li>" for m in item.get("motivos") or [])
        linhas_html.append(f"""
        <tr>
          <td style="padding:16px 0;border-bottom:1px solid #e7e7ea;">
            <div style="font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#a9872a;font-weight:600;margin-bottom:4px;">
              {item.get("criterio_nome", "")}
            </div>
            <div style="font-size:15px;font-weight:600;color:#0f0f11;margin-bottom:4px;">
              {item.get("orgao") or "Órgão não informado"} · {item.get("uf") or "—"}
            </div>
            <div style="font-size:13.5px;color:#5b5b62;line-height:1.5;margin-bottom:8px;">
              {item.get("objeto") or ""}
            </div>
            <div style="font-size:12.5px;color:#8b8b93;margin-bottom:8px;">
              Valor estimado: <strong style="color:#2f6b4f;">{_formatar_valor(item.get("valor_estimado"))}</strong>
              &nbsp;·&nbsp; Encerramento: {item.get("data_encerramento_proposta") or "não informado"}
            </div>
            <ul style="margin:0 0 10px;padding-left:18px;font-size:12.5px;color:#5b5b62;">
              {motivos_html}
            </ul>
            {f'<a href="{item.get("link_edital")}" style="font-size:13px;font-weight:600;color:#0f0f11;border-bottom:1.5px solid #d4af37;text-decoration:none;">Ver edital →</a>' if item.get("link_edital") else ""}
          </td>
        </tr>""")

    return f"""
    <div style="font-family:-apple-system,Segoe UI,Arial,sans-serif;max-width:600px;margin:0 auto;background:#f7f7f7;padding:24px;">
      <div style="background:linear-gradient(160deg,#0f0f11 0%,#000 100%);border-radius:10px 10px 0 0;padding:22px 24px;">
        <div style="font-size:18px;font-weight:700;">
          <span style="color:#fff;">Licit</span><span style="color:#d4af37;">Tracker</span>
        </div>
        <div style="font-size:12.5px;color:#b5b5bd;margin-top:4px;">
          Resumo diário de licitações para {empresa_nome}
        </div>
      </div>
      <div style="background:#fff;border:1px solid #e7e7ea;border-top:none;border-radius:0 0 10px 10px;padding:8px 24px;">
        <table style="width:100%;border-collapse:collapse;">
          {"".join(linhas_html)}
        </table>
        <p style="font-size:11.5px;color:#8b8b93;padding:16px 0 4px;">
          Você recebeu este e-mail porque tem notificações ativadas no LicitTracker.
          Pode desativar a qualquer momento no menu da sua conta.
        </p>
      </div>
    </div>
    """


def montar_email_alerta_vencimento(empresa_nome: str, itens: list[dict]) -> str:
    """Monta o HTML do alerta de vencimento de documentos/certidões. Cada
    item de `itens` é um dict com: nome, categoria, dias_restantes
    (negativo = já venceu)."""
    linhas_html = []
    for item in itens:
        dias = item.get("dias_restantes", 0)
        if dias < 0:
            situacao = f"venceu há {abs(dias)} dia(s)"
            cor = "#b14b3b"
        elif dias == 0:
            situacao = "vence hoje"
            cor = "#b14b3b"
        else:
            situacao = f"vence em {dias} dia(s)"
            cor = "#a9872a" if dias <= 15 else "#2f6b4f"

        linhas_html.append(f"""
        <tr>
          <td style="padding:16px 0;border-bottom:1px solid #e7e7ea;">
            <div style="font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#a9872a;font-weight:600;margin-bottom:4px;">
              {item.get("categoria", "")}
            </div>
            <div style="font-size:15px;font-weight:600;color:#0f0f11;margin-bottom:4px;">
              {item.get("nome") or "Documento"}
            </div>
            <div style="font-size:13px;font-weight:600;color:{cor};">
              {situacao}
            </div>
          </td>
        </tr>""")

    return f"""
    <div style="font-family:-apple-system,Segoe UI,Arial,sans-serif;max-width:600px;margin:0 auto;background:#f7f7f7;padding:24px;">
      <div style="background:linear-gradient(160deg,#0f0f11 0%,#000 100%);border-radius:10px 10px 0 0;padding:22px 24px;">
        <div style="font-size:18px;font-weight:700;">
          <span style="color:#fff;">Licit</span><span style="color:#d4af37;">Tracker</span>
        </div>
        <div style="font-size:12.5px;color:#b5b5bd;margin-top:4px;">
          Documentos e certidões próximos do vencimento — {empresa_nome}
        </div>
      </div>
      <div style="background:#fff;border:1px solid #e7e7ea;border-top:none;border-radius:0 0 10px 10px;padding:8px 24px;">
        <table style="width:100%;border-collapse:collapse;">
          {"".join(linhas_html)}
        </table>
        <p style="font-size:11.5px;color:#8b8b93;padding:16px 0 4px;">
          Você recebeu este e-mail porque tem notificações ativadas no LicitTracker.
          Pode desativar a qualquer momento no menu da sua conta.
        </p>
      </div>
    </div>
    """
