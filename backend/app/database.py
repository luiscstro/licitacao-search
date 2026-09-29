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

# pool_pre_ping: testa a conexão (SELECT 1) antes de cada uso e reconecta
# sozinho se estiver morta, em vez de estourar erro na query real. Necessário
# porque o Postgres gerenciado (Neon) fecha conexões ociosas do seu lado sem
# avisar o pool do SQLAlchemy — sem isso, a primeira query após um período
# de inatividade falha com "SSL connection has been closed unexpectedly".
# pool_recycle descarta proativamente conexões com mais de 5 min, pra nunca
# depender de uma conexão sobreviver mais tempo que o timeout do Neon.
pool_kwargs = {} if DATABASE_URL.startswith("sqlite") else {"pool_pre_ping": True, "pool_recycle": 300}

engine = create_engine(DATABASE_URL, connect_args=connect_args, **pool_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency do FastAPI — abre uma sessão por requisição e fecha no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
