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


class EmpresaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str


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
    exigir_pregao: bool = True


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
    exigir_pregao: Optional[bool] = None
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