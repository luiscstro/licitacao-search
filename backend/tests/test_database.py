"""Testes pra app/database.py — normalização de DATABASE_URL e driver Postgres
instalado. Não conecta em nenhum banco de verdade (SQLAlchemy só resolve o
dialeto/driver ao tentar conectar, não ao criar o Engine)."""

from sqlalchemy import create_engine

from app.database import normalizar_database_url


class TestNormalizarDatabaseUrl:
    def test_esquema_antigo_postgres_vira_postgresql(self):
        url = "postgres://usuario:senha@host:5432/banco"
        assert normalizar_database_url(url) == "postgresql://usuario:senha@host:5432/banco"

    def test_esquema_postgresql_ja_correto_fica_igual(self):
        url = "postgresql://usuario:senha@host:5432/banco"
        assert normalizar_database_url(url) == url

    def test_sqlite_fica_igual(self):
        url = "sqlite:///./licitacoes_saas.db"
        assert normalizar_database_url(url) == url

    def test_so_troca_a_primeira_ocorrencia(self):
        # a senha/nome do banco poderiam conter a substring "postgres://" —
        # só o esquema no início deve ser trocado.
        url = "postgres://usuario:senha@host/postgres://banco"
        assert normalizar_database_url(url) == "postgresql://usuario:senha@host/postgres://banco"


def test_driver_psycopg2_resolve_para_url_postgresql_bare():
    """Confirma que uma DATABASE_URL "postgresql://..." (formato mais comum,
    sem sufixo de driver) resolve pro driver psycopg2-binary instalado —
    sem precisar o usuário editar a connection string."""
    engine = create_engine("postgresql://usuario:senha@localhost:5432/banco")
    assert engine.dialect.driver == "psycopg2"


def test_driver_psycopg_resolve_para_url_com_sufixo_psycopg():
    """Confirma que uma DATABASE_URL "postgresql+psycopg://..." (formato que
    o Neon também oferece) resolve pro driver psycopg (v3) instalado — bug
    real encontrado em produção: só tínhamos psycopg2-binary instalado, e
    o deploy quebrou com "ModuleNotFoundError: No module named 'psycopg'"
    porque a URL usada tinha esse sufixo."""
    engine = create_engine("postgresql+psycopg://usuario:senha@localhost:5432/banco")
    assert engine.dialect.driver == "psycopg"
