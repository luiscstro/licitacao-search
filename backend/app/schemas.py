from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class UsuarioCriar(BaseModel):
    email: EmailStr
    senha: str
    nome_empresa: Optional[str] = None


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    nome_empresa: Optional[str]
    criado_em: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CriterioBase(BaseModel):
    nome: str = "Meu critério"
    palavra_obrigatoria: str
    palavras_bonus: str = ""
    valor_minimo: float = 0
    valor_maximo: float = 999_999_999
    estados_permitidos: str = ""
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


# ---------- Licitação (resultado filtrado) ----------

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