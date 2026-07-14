"""
API principal — Buscador de Licitações (SaaS)

Pra rodar localmente:
    uvicorn app.main:app --reload

Depois abra http://127.0.0.1:8000/docs — o FastAPI gera uma interface
interativa sozinho, onde dá pra testar todos os endpoints sem precisar
de frontend nenhum ainda.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import models, schemas, auth, scoring
from .database import engine, get_db, Base

# Cria as tabelas no banco se ainda não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Buscador de Licitações API", version="1.0")

# CORS: permite que um frontend (rodando em outro endereço/porta) chame essa API.
# Em produção, troque "*" pela URL real do seu frontend, por segurança.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Autenticação
# ============================================================

@app.post("/auth/registrar", response_model=schemas.UsuarioSaida, status_code=201)
def registrar(dados: schemas.UsuarioCriar, db: Session = Depends(get_db)):
    ja_existe = db.query(models.User).filter(models.User.email == dados.email).first()
    if ja_existe:
        raise HTTPException(status_code=400, detail="Já existe uma conta com esse e-mail")

    usuario = models.User(
        email=dados.email,
        senha_hash=auth.hash_senha(dados.senha),
        nome_empresa=dados.nome_empresa,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@app.post("/auth/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm espera campos "username" e "password" —
    # aqui tratamos "username" como sendo o e-mail.
    usuario = db.query(models.User).filter(models.User.email == form.username).first()
    if not usuario or not auth.verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )
    token = auth.criar_token({"sub": usuario.email})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=schemas.UsuarioSaida)
def meu_perfil(usuario: models.User = Depends(auth.usuario_atual)):
    return usuario


# ============================================================
# Critérios (filtros de cada cliente)
# ============================================================

@app.get("/criterios", response_model=list[schemas.CriterioSaida])
def listar_criterios(
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    return db.query(models.Criterio).filter(models.Criterio.user_id == usuario.id).all()


@app.post("/criterios", response_model=schemas.CriterioSaida, status_code=201)
def criar_criterio(
    dados: schemas.CriterioCriar,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    criterio = models.Criterio(**dados.model_dump(), user_id=usuario.id)
    db.add(criterio)
    db.commit()
    db.refresh(criterio)
    return criterio


@app.put("/criterios/{criterio_id}", response_model=schemas.CriterioSaida)
def atualizar_criterio(
    criterio_id: int,
    dados: schemas.CriterioAtualizar,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    criterio = db.query(models.Criterio).filter(
        models.Criterio.id == criterio_id, models.Criterio.user_id == usuario.id
    ).first()
    if not criterio:
        raise HTTPException(status_code=404, detail="Critério não encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(criterio, campo, valor)

    db.commit()
    db.refresh(criterio)
    return criterio


@app.delete("/criterios/{criterio_id}", status_code=204)
def deletar_criterio(
    criterio_id: int,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    criterio = db.query(models.Criterio).filter(
        models.Criterio.id == criterio_id, models.Criterio.user_id == usuario.id
    ).first()
    if not criterio:
        raise HTTPException(status_code=404, detail="Critério não encontrado")
    db.delete(criterio)
    db.commit()


# ============================================================
# Licitações (resultado filtrado, por critério)
# ============================================================

@app.get("/licitacoes", response_model=list[schemas.LicitacaoSaida])
def listar_licitacoes(
    criterio_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    """
    Retorna as licitações ativas que batem com os critérios do usuário logado.
    Se `criterio_id` for informado, filtra só por aquele critério específico;
    senão, aplica TODOS os critérios ativos do usuário e junta os resultados.
    """
    query_criterios = db.query(models.Criterio).filter(
        models.Criterio.user_id == usuario.id, models.Criterio.ativo == True  # noqa: E712
    )
    if criterio_id is not None:
        query_criterios = query_criterios.filter(models.Criterio.id == criterio_id)

    criterios = query_criterios.all()
    if not criterios:
        return []

    licitacoes_ativas = db.query(models.Licitacao).filter(models.Licitacao.ativa == True).all()  # noqa: E712

    resultados = {}
    for licitacao in licitacoes_ativas:
        melhor_score = 0
        melhores_motivos = []
        passou_algum = False

        for criterio in criterios:
            passou, motivos, score = scoring.aplicar_criterio(licitacao, criterio)
            if passou and score > melhor_score:
                passou_algum = True
                melhor_score = score
                melhores_motivos = motivos

        if passou_algum:
            saida = schemas.LicitacaoSaida.model_validate(licitacao)
            saida.score = melhor_score
            saida.motivos = melhores_motivos
            resultados[licitacao.numero_controle] = saida

    return sorted(resultados.values(), key=lambda r: r.score, reverse=True)


@app.get("/")
def raiz():
    return {"status": "ok", "mensagem": "API do Buscador de Licitações no ar. Veja /docs"}