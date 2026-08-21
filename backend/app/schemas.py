"""
Schemas Pydantic — definem o formato dos dados que entram e saem da API.
FastAPI usa isso pra validar automaticamente e gerar a documentação (/docs).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


# ---------- Usuário / Empresa / Equipe ----------

class UsuarioCriar(BaseModel):
    email: EmailStr
    senha: str
    nome_empresa: Optional[str] = None
    token_convite: Optional[str] = None  # se vier, entra numa empresa já existente


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    papel: str
    empresa_id: int
    criado_em: datetime
    receber_notificacoes: bool = True


class PreferenciasAtualizar(BaseModel):
    receber_notificacoes: Optional[bool] = None


class EmpresaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    endereco_logradouro: Optional[str] = None
    endereco_numero: Optional[str] = None
    endereco_complemento: Optional[str] = None
    endereco_bairro: Optional[str] = None
    endereco_cidade: Optional[str] = None
    endereco_uf: Optional[str] = None
    endereco_cep: Optional[str] = None
    representante_nome: Optional[str] = None
    representante_cpf: Optional[str] = None
    representante_cargo: Optional[str] = None
    representante_email: Optional[str] = None
    representante_telefone: Optional[str] = None
    situacao_cadastral: Optional[str] = None
    cnpj_sincronizado_em: Optional[datetime] = None


class EmpresaAtualizar(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    endereco_logradouro: Optional[str] = None
    endereco_numero: Optional[str] = None
    endereco_complemento: Optional[str] = None
    endereco_bairro: Optional[str] = None
    endereco_cidade: Optional[str] = None
    endereco_uf: Optional[str] = None
    endereco_cep: Optional[str] = None
    representante_nome: Optional[str] = None
    representante_cpf: Optional[str] = None
    representante_cargo: Optional[str] = None
    representante_email: Optional[str] = None
    representante_telefone: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ConvidarEntrada(BaseModel):
    email: EmailStr


class ConviteSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email_convidado: str
    token: str
    usado: bool
    criado_em: datetime


class MembroEquipeSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    papel: str
    criado_em: datetime


# ---------- Critério ----------

class CriterioBase(BaseModel):
    nome: str = "Meu critério"
    palavra_obrigatoria: str
    palavras_bonus: str = ""
    valor_minimo: float = 0
    valor_maximo: float = 999_999_999
    estados_permitidos: str = ""  # ex: "MA,PI,PA,TO,CE" — vazio = todos os estados
    exigir_dedicacao_exclusiva: bool = True
    modalidades_permitidas: str = ""  # ex: "Pregão,Dispensa" — vazio = qualquer modalidade


class CriterioCriar(CriterioBase):
    pass


class CriterioAtualizar(BaseModel):
    nome: Optional[str] = None
    palavra_obrigatoria: Optional[str] = None
    palavras_bonus: Optional[str] = None
    valor_minimo: Optional[float] = None
    valor_maximo: Optional[float] = None
    estados_permitidos: Optional[str] = None
    exigir_dedicacao_exclusiva: Optional[bool] = None
    modalidades_permitidas: Optional[str] = None
    ativo: Optional[bool] = None


class CriterioSaida(CriterioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ativo: bool
    criado_em: datetime


# ---------- Licitação (resultado filtrado/buscado) ----------

class LicitacaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    numero_controle: str
    orgao: str
    cidade: Optional[str]
    uf: Optional[str]
    objeto: str
    valor_estimado: float
    modalidade: Optional[str]
    data_encerramento_proposta: Optional[str]
    link_edital: str
    score: float = 0
    motivos: list[str] = []
    favoritada: bool = False


# ---------- Pipeline (mini-CRM, compartilhado pela empresa) ----------

class OportunidadeSaida(LicitacaoSaida):
    status: str = "monitorando"
    status_atualizado_em: Optional[datetime] = None
    atualizado_por_email: str = ""


class AtualizarStatusEntrada(BaseModel):
    status: str


# ---------- Licitações paginadas ----------

class LicitacoesPaginadas(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int
    itens: list[LicitacaoSaida]


# ---------- Favoritos ----------

class FavoritoCriar(BaseModel):
    numero_controle: str


class FavoritoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    numero_controle: str
    criado_em: datetime


# ---------- Comentários ----------

class ComentarioCriar(BaseModel):
    numero_controle: str
    texto: str


class ComentarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    texto: str
    criado_em: datetime
    autor_email: str = ""


# ---------- Estatísticas (gráficos do dashboard) ----------

class ContagemPorChave(BaseModel):
    chave: str
    quantidade: int


class EstatisticasSaida(BaseModel):
    total: int
    valor_total_estimado: float
    por_uf: list[ContagemPorChave]
    por_modalidade: list[ContagemPorChave]
    por_mes: list[ContagemPorChave]


# ---------- Documentos de habilitação / certidões ----------

class DocumentoAtualizar(BaseModel):
    nome: Optional[str] = None
    categoria: Optional[str] = None
    data_emissao: Optional[datetime] = None
    data_validade: Optional[datetime] = None


class DocumentoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    categoria: str
    nome: str
    nome_arquivo_original: str
    tamanho_bytes: int
    data_emissao: Optional[datetime] = None
    data_validade: Optional[datetime] = None
    status: str = "sem_data"
    criado_em: datetime
    atualizado_em: datetime
    enviado_por_email: str = ""


class DocumentoHistoricoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    nome_arquivo_original: str
    data_emissao: Optional[datetime] = None
    data_validade: Optional[datetime] = None
    substituido_em: datetime
    substituido_por_email: str = ""


class ContagemPorStatus(BaseModel):
    status: str
    quantidade: int


class AtividadeRecente(BaseModel):
    nome: str
    categoria: str
    atualizado_em: datetime
    atualizado_por_email: str = ""


class IndicadoresDocumentosSaida(BaseModel):
    por_status: list[ContagemPorStatus]
    por_categoria: list[ContagemPorChave]
    ultimas_atualizacoes: list[AtividadeRecente]