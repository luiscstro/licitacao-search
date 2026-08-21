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

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Cadastro único (dados fiscais), preenchido pelo owner ou sincronizado
    # automaticamente via CNPJ (dados abertos da Receita Federal).
    cnpj = Column(String, nullable=True)
    inscricao_estadual = Column(String, nullable=True)
    inscricao_municipal = Column(String, nullable=True)
    endereco_logradouro = Column(String, nullable=True)
    endereco_numero = Column(String, nullable=True)
    endereco_complemento = Column(String, nullable=True)
    endereco_bairro = Column(String, nullable=True)
    endereco_cidade = Column(String, nullable=True)
    endereco_uf = Column(String, nullable=True)
    endereco_cep = Column(String, nullable=True)
    representante_nome = Column(String, nullable=True)
    representante_cpf = Column(String, nullable=True)
    representante_cargo = Column(String, nullable=True)
    representante_email = Column(String, nullable=True)
    representante_telefone = Column(String, nullable=True)
    situacao_cadastral = Column(String, nullable=True)
    cnpj_sincronizado_em = Column(DateTime, nullable=True)

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
    receber_notificacoes = Column(Boolean, default=True)

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

    # Trechos de nome de modalidade que devem aparecer (ex: "Pregão,Dispensa").
    # Vazio = aceita qualquer modalidade.
    modalidades_permitidas = Column(String, default="")

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
    valor_estimado = Column(Float, default=0, index=True)
    modalidade = Column(String, index=True)
    data_abertura_proposta = Column(String, nullable=True)
    data_encerramento_proposta = Column(String, nullable=True)
    link_edital = Column(String, default="")

    # Texto de busca pré-processado (minúsculo, sem acento), calculado uma
    # vez pelo coletor em vez de reprocessar a cada consulta:
    # - texto_busca_objeto: SÓ objeto + informação complementar. É o que
    #   define "do que essa licitação trata" — usado pros critérios
    #   (palavra obrigatória, bônus, DEMO), pra evitar que o nome do órgão
    #   comprador (ex: "Coordenadoria de Apoio Administrativo") faça uma
    #   licitação bater por engano.
    # - texto_busca: objeto + órgão + cidade + informação complementar.
    #   Mais abrangente — usado só na busca LIVRE, onde faz sentido
    #   encontrar por nome de cidade ou órgão também.
    texto_busca_objeto = Column(Text, default="", index=True)
    texto_busca = Column(Text, default="", index=True)

    primeira_vez_vista = Column(DateTime, default=datetime.utcnow)
    ultima_vez_vista = Column(DateTime, default=datetime.utcnow)
    ativa = Column(Boolean, default=True, index=True)

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


class Oportunidade(Base):
    """Pipeline de acompanhamento (mini-CRM) — diferente de Favorito, é
    compartilhada pela empresa toda (não por usuário), igual Criterio.
    Criada automaticamente quando qualquer usuário da empresa favorita uma
    licitação; segue existindo mesmo se o favorito original for removido."""

    __tablename__ = "oportunidades"
    __table_args__ = (UniqueConstraint("empresa_id", "numero_controle", name="uq_oportunidade_por_empresa"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    numero_controle = Column(String, ForeignKey("licitacoes.numero_controle"), nullable=False)
    status = Column(String, default="monitorando")
    status_atualizado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    atualizado_por = relationship("User")


CATEGORIAS_DOCUMENTO = ["juridica", "fiscal", "trabalhista", "economico_financeira", "tecnica", "outra"]
LIMIARES_ALERTA_VENCIMENTO = [30, 15, 7, 1, 0]


class DocumentoHabilitacao(Base):
    """Documento de habilitação ou certidão, num único modelo flexível —
    a empresa cadastra qualquer nome (não é uma lista travada de tipos).
    Certidões são só documentos com data_validade preenchida."""

    __tablename__ = "documentos_habilitacao"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    categoria = Column(String, nullable=False, default="outra")
    nome = Column(String, nullable=False)
    nome_arquivo_original = Column(String, nullable=False)
    caminho_arquivo = Column(String, nullable=False)
    tamanho_bytes = Column(Integer, default=0)
    data_emissao = Column(DateTime, nullable=True)
    data_validade = Column(DateTime, nullable=True)
    enviado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow)
    ultimo_alerta_dias = Column(Integer, nullable=True)

    enviado_por = relationship("User")

    @property
    def status(self) -> str:
        if not self.data_validade:
            return "sem_data"
        dias_restantes = (self.data_validade - datetime.utcnow()).days
        if dias_restantes < 0:
            return "vencida"
        if dias_restantes <= 30:
            return "vencendo"
        return "valida"


class DocumentoHistorico(Base):
    """Versão anterior de um DocumentoHabilitacao, arquivada quando o
    arquivo é substituído — histórico simples de emissões."""

    __tablename__ = "documentos_historico"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    documento_id = Column(Integer, ForeignKey("documentos_habilitacao.id"), nullable=True)
    nome = Column(String, nullable=False)
    nome_arquivo_original = Column(String, nullable=False)
    caminho_arquivo = Column(String, nullable=False)
    data_emissao = Column(DateTime, nullable=True)
    data_validade = Column(DateTime, nullable=True)
    substituido_em = Column(DateTime, default=datetime.utcnow)
    substituido_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    substituido_por = relationship("User")
