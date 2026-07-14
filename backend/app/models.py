from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    nome_empresa = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    ativo = Column(Boolean, default=True)

    criterios = relationship("Criterio", back_populates="dono", cascade="all, delete-orphan")


class Criterio(Base):

    __tablename__ = "criterios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    nome = Column(String, nullable=False, default="Meu critério")

    palavra_obrigatoria = Column(String, nullable=False)

    palavras_bonus = Column(String, default="")

    valor_minimo = Column(Float, default=0)
    valor_maximo = Column(Float, default=999_999_999)

    estados_permitidos = Column(String, default="")

    exigir_dedicacao_exclusiva = Column(Boolean, default=True)
    exigir_pregao = Column(Boolean, default=True)

    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    dono = relationship("User", back_populates="criterios")


class Licitacao(Base):
    __tablename__ = "licitacoes"

    numero_controle = Column(String, primary_key=True)
    orgao = Column(String)
    cidade = Column(String)
    uf = Column(String, index=True)
    objeto = Column(Text)
    informacao_complementar = Column(Text, default="")
    valor_estimado = Column(Float, default=0)
    modalidade = Column(String)
    data_abertura_proposta = Column(String, nullable=True)
    data_encerramento_proposta = Column(String, nullable=True)
    link_edital = Column(String, default="")

    primeira_vez_vista = Column(DateTime, default=datetime.utcnow)
    ultima_vez_vista = Column(DateTime, default=datetime.utcnow)
    ativa = Column(Boolean, default=True)