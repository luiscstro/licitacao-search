"""
Headers de segurança de resposta HTTP.

Não substitui HTTPS/HSTS (isso é responsabilidade do proxy/hospedagem
quando o app for publicado) — cobre só o que dá pra garantir na própria
aplicação, independente de onde for hospedado.
"""

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        resposta = await call_next(request)
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return resposta


def setup_security_headers(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
