"""
Modelos do banco de dados.

- Empresa: a "conta" que assina o produto — pode ter vários usuários (equipe).
- User: uma pessoa dentro de uma Empresa. Pode ser "owner" (dono, pode convidar
  gente e gerenciar a equipe) ou "membro".
- Criterio: filtros configurados por EMPRESA (compartilhados pela equipe toda).
- Licitacao: base compartilhada de licitações coletadas do PNCP — global,
  não pertence a nenhuma empresa específica.
- Favorito: uma licitação marcada como favorita por um usuário específico.
- Comentario: anotações que um usuário deixa numa licitação, visível pra
  equipe toda (mesma empresa).
- ConviteEquipe: token de convite pra alguém entrar numa empresa existente.
"""

import secrets
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text,
    UniqueConstraint
)
from sqlalchemy.orm import relationship

from .database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    usuarios = relationship("User", back_populates="empresa")
    criterios = relationship("Criterio", back_populates="empresa", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    papel = Column(String, default="owner")  # "owner" ou "membro"
    criado_em = Column(DateTime, default=datetime.utcnow)
    ativo = Column(Boolean, default=True)

    empresa = relationship("Empresa", back_populates="usuarios")
    favoritos = relationship("Favorito", back_populates="usuario", cascade="all, delete-orphan")
    comentarios = relationship("Comentario", back_populates="usuario", cascade="all, delete-orphan")


class ConviteEquipe(Base):
    """Token que um 'owner' gera pra convidar alguém a entrar na empresa dele."""
    __tablename__ = "convites_equipe"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    email_convidado = Column(String, nullable=False)
    token = Column(String, unique=True, index=True, default=lambda: secrets.token_urlsafe(24))
    usado = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)


class Criterio(Base):
    """
    Um conjunto de filtros configurado pela empresa (compartilhado pela
    equipe toda — não é individual por usuário).
    """
    __tablename__ = "criterios"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)

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

    empresa = relationship("Empresa", back_populates="criterios")


class Licitacao(Base):
    """Base compartilhada de licitações coletadas do PNCP — global."""
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

    favoritos = relationship("Favorito", back_populates="licitacao", cascade="all, delete-orphan")
    comentarios = relationship("Comentario", back_populates="licitacao", cascade="all, delete-orphan")


class Favorito(Base):
    __tablename__ = "favoritos"
    __table_args__ = (UniqueConstraint("user_id", "numero_controle", name="uq_favorito_por_usuario"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    numero_controle = Column(String, ForeignKey("licitacoes.numero_controle"), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("User", back_populates="favoritos")
    licitacao = relationship("Licitacao", back_populates="favoritos")


class Comentario(Base):
    __tablename__ = "comentarios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    numero_controle = Column(String, ForeignKey("licitacoes.numero_controle"), nullable=False)
    texto = Column(Text, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("User", back_populates="comentarios")
    licitacao = relationship("Licitacao", back_populates="comentarios")