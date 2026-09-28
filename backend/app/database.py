"""
Configuração do banco de dados.

Usa SQLite por padrão (arquivo local, zero configuração) — mas como usamos
SQLAlchemy, migrar pra PostgreSQL (ex: em produção, quando o SQLite local não
é acessível pra um serviço remoto) é só trocar a variável DATABASE_URL, sem
reescrever nada do resto do código.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def normalizar_database_url(url: str) -> str:
    """Alguns provedores (ex: Heroku, e versões antigas do Render/Neon) ainda
    devolvem a connection string com o esquema antigo "postgres://", que o
    SQLAlchemy 1.4+ não aceita mais — normaliza pro esquema atual."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


# Em produção, defina a variável de ambiente DATABASE_URL apontando pra um
# Postgres, ex: postgresql://usuario:senha@host:5432/licitacoes
DATABASE_URL = normalizar_database_url(os.getenv("DATABASE_URL", "sqlite:///./licitacoes_saas.db"))

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency do FastAPI — abre uma sessão por requisição e fecha no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
