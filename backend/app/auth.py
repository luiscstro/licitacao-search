"""
Autenticação: hash de senha (nunca guardamos senha em texto puro), tokens
JWT de acesso (curta duração) e refresh tokens (revogáveis, guardados no
banco só como hash) pra renovar o acesso sem pedir login de novo.

Duas proteções contra abuso:
- Rate limiting simples em memória no login, contra força bruta.
- Access token de vida curta (EXPIRACAO_TOKEN_MINUTOS) + refresh token
  revogável — se um token vazar, o estrago é limitado pela vida curta do
  access token, e o refresh token pode ser revogado (logout, ou detecção
  de reuso pós-rotação) sem esperar expirar sozinho.
"""

import hashlib
import os
import secrets
import threading
import time
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import models
from .database import get_db

# Em produção, defina SECRET_KEY como variável de ambiente (mesmo padrão do
# SMTP_* em email_utils.py). Sem ela, geramos uma chave aleatória só pra essa
# execução — nunca uma string fixa/previsível no código — mas isso invalida
# todos os tokens emitidos a cada reinício do servidor, então é só pra
# desenvolvimento local mesmo.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print(
        "AVISO: SECRET_KEY nao definida - usando uma chave aleatoria temporaria "
        "so para esta execucao (todos os logins serao invalidados ao reiniciar "
        "o servidor). Defina SECRET_KEY como variavel de ambiente para producao "
        "ou para manter sessoes entre reinicios."
    )
ALGORITHM = "HS256"
EXPIRACAO_TOKEN_MINUTOS = 60  # access token de vida curta — use /auth/refresh pra renovar
EXPIRACAO_REFRESH_TOKEN_DIAS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_senha(senha: str) -> str:
    senha_bytes = senha.encode("utf-8")[:72]  # bcrypt só aceita até 72 bytes
    return bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha_texto: str, senha_hash: str) -> bool:
    senha_bytes = senha_texto.encode("utf-8")[:72]
    return bcrypt.checkpw(senha_bytes, senha_hash.encode("utf-8"))


def criar_token(dados: dict) -> str:
    dados_copia = dados.copy()
    expira_em = datetime.utcnow() + timedelta(minutes=EXPIRACAO_TOKEN_MINUTOS)
    dados_copia.update({"exp": expira_em})
    return jwt.encode(dados_copia, SECRET_KEY, algorithm=ALGORITHM)


def usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """
    Dependency usada nos endpoints protegidos. Lê o token JWT do header
    Authorization, valida, e retorna o usuário correspondente — ou
    recusa a requisição com 401 se o token for inválido/expirado.
    """
    excecao_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise excecao_credenciais
    except JWTError:
        raise excecao_credenciais

    usuario = db.query(models.User).filter(models.User.email == email).first()
    if usuario is None:
        raise excecao_credenciais
    return usuario


# ============================================================
# Rate limiting do login (proteção simples contra força bruta)
# ============================================================

MAX_TENTATIVAS_LOGIN = 5
JANELA_BLOQUEIO_SEGUNDOS = 15 * 60  # 15 min

_tentativas_login: dict[str, list[float]] = {}
_tentativas_lock = threading.Lock()


def verificar_rate_limit_login(identificador: str) -> None:
    """Levanta 429 se `identificador` (o e-mail tentado) já teve
    MAX_TENTATIVAS_LOGIN falhas dentro dos últimos JANELA_BLOQUEIO_SEGUNDOS.
    Não é por IP: sem um proxy configurado na frente garantindo
    X-Forwarded-For confiável, o e-mail é o identificador que temos —
    suficiente pra frear força bruta contra uma conta específica."""
    agora = time.monotonic()
    with _tentativas_lock:
        tentativas = [t for t in _tentativas_login.get(identificador, []) if agora - t < JANELA_BLOQUEIO_SEGUNDOS]
        _tentativas_login[identificador] = tentativas
        if len(tentativas) >= MAX_TENTATIVAS_LOGIN:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Muitas tentativas de login. Tente de novo em {JANELA_BLOQUEIO_SEGUNDOS // 60} minutos.",
            )


def registrar_tentativa_login_falha(identificador: str) -> None:
    with _tentativas_lock:
        _tentativas_login.setdefault(identificador, []).append(time.monotonic())


def limpar_tentativas_login(identificador: str) -> None:
    with _tentativas_lock:
        _tentativas_login.pop(identificador, None)


# ============================================================
# Refresh token (revogável, guardado no banco só como hash)
# ============================================================


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def criar_refresh_token(db: Session, usuario: models.User) -> str:
    token = secrets.token_urlsafe(48)
    db.add(
        models.RefreshToken(
            token_hash=_hash_refresh_token(token),
            user_id=usuario.id,
            expira_em=datetime.utcnow() + timedelta(days=EXPIRACAO_REFRESH_TOKEN_DIAS),
        )
    )
    db.commit()
    return token


def validar_e_rotacionar_refresh_token(db: Session, token: str) -> tuple[models.User, str]:
    """Valida um refresh token (existe, não expirou, não foi revogado) e o
    substitui por um novo (rotação): o token usado é revogado na hora, então
    reutilizá-lo depois disso sempre falha — inclusive detectando um token
    roubado sendo usado depois do dono legítimo já ter renovado."""
    excecao = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido ou expirado")

    registro = (
        db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == _hash_refresh_token(token)).first()
    )
    if not registro or registro.revogado_em is not None or registro.expira_em < datetime.utcnow():
        raise excecao

    registro.revogado_em = datetime.utcnow()
    usuario = db.query(models.User).filter(models.User.id == registro.user_id).first()
    db.commit()
    if not usuario:
        raise excecao

    novo_token = criar_refresh_token(db, usuario)
    return usuario, novo_token


def revogar_refresh_token(db: Session, token: str) -> None:
    """Usado no logout. Silencioso se o token já não existir/estiver revogado
    — logout não precisa informar isso ao cliente."""
    registro = (
        db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == _hash_refresh_token(token)).first()
    )
    if registro and registro.revogado_em is None:
        registro.revogado_em = datetime.utcnow()
        db.commit()
