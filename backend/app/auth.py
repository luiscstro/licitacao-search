import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db

# ⚠️ Em produção, defina isso como variável de ambiente — nunca deixe fixo
# no código quando for publicar de verdade.
SECRET_KEY = os.getenv("SECRET_KEY", "chave-temporaria-troque-isso-em-producao")
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