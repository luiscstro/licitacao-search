"""
Autenticação: hash de senha (nunca guardamos senha em texto puro) e
tokens JWT (o "crachá" que o cliente usa pra provar que já fez login,
sem precisar mandar email+senha em toda requisição).
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
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
EXPIRACAO_TOKEN_MINUTOS = 60 * 24 * 7  # 7 dias

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
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise excecao_credenciais
    except JWTError:
        raise excecao_credenciais

    usuario = db.query(models.User).filter(models.User.email == email).first()
    if usuario is None:
        raise excecao_credenciais
    return usuario