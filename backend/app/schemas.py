"""
Schemas Pydantic — definem o formato dos dados que entram e saem da API.
FastAPI usa isso pra validar automaticamente e gerar a documentação (/docs).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

# ---------- Usuário / Empresa / Equipe ----------


class UsuarioCriar(BaseModel):
    email: EmailStr
    senha: str
    nome_empresa: str | None = None
    token_convite: str | None = None  # se vier, entra numa empresa já existente


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
    receber_notificacoes: bool | None = None


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
    modalidades_permitidas: str = ""  # ex: "Pregão,Dispensa" — vazio = qualquer modalidade


class CriterioCriar(CriterioBase):
    pass


class CriterioAtualizar(BaseModel):
    nome: str | None = None
    palavra_obrigatoria: str | None = None
    palavras_bonus: str | None = None
    valor_minimo: float | None = None
    valor_maximo: float | None = None
    estados_permitidos: str | None = None
    exigir_dedicacao_exclusiva: bool | None = None
    modalidades_permitidas: str | None = None
    ativo: bool | None = None


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
    cidade: str | None
    uf: str | None
    objeto: str
    valor_estimado: float
    modalidade: str | None
    data_encerramento_proposta: str | None
    link_edital: str
    score: float = 0
    motivos: list[str] = []
    favoritada: bool = False


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
