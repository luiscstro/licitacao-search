"""
API principal — Buscador de Licitações (SaaS)

Pra rodar localmente:
    uvicorn app.main:app --reload

Depois abra http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import models, schemas, auth, scoring
from .database import engine, get_db, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Buscador de Licitações API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def exigir_owner(usuario: models.User = Depends(auth.usuario_atual)) -> models.User:
    if usuario.papel != "owner":
        raise HTTPException(status_code=403, detail="Só o dono da conta pode fazer isso")
    return usuario


# ============================================================
# Autenticação / Empresa / Equipe
# ============================================================

@app.post("/auth/registrar", response_model=schemas.UsuarioSaida, status_code=201)
def registrar(dados: schemas.UsuarioCriar, db: Session = Depends(get_db)):
    ja_existe = db.query(models.User).filter(models.User.email == dados.email).first()
    if ja_existe:
        raise HTTPException(status_code=400, detail="Já existe uma conta com esse e-mail")

    if dados.token_convite:
        # Entrando numa empresa já existente via convite
        convite = db.query(models.ConviteEquipe).filter(
            models.ConviteEquipe.token == dados.token_convite,
            models.ConviteEquipe.usado == False,  # noqa: E712
        ).first()
        if not convite:
            raise HTTPException(status_code=400, detail="Convite inválido ou já utilizado")

        usuario = models.User(
            email=dados.email,
            senha_hash=auth.hash_senha(dados.senha),
            empresa_id=convite.empresa_id,
            papel="membro",
        )
        convite.usado = True
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    # Criando uma empresa nova, e esse usuário vira o "owner" dela
    empresa = models.Empresa(nome=dados.nome_empresa or dados.email.split("@")[0])
    db.add(empresa)
    db.flush()  # gera o id da empresa sem precisar commitar ainda

    usuario = models.User(
        email=dados.email,
        senha_hash=auth.hash_senha(dados.senha),
        empresa_id=empresa.id,
        papel="owner",
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@app.post("/auth/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.User).filter(models.User.email == form.username).first()
    if not usuario or not auth.verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos")
    token = auth.criar_token({"sub": usuario.email})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=schemas.UsuarioSaida)
def meu_perfil(usuario: models.User = Depends(auth.usuario_atual)):
    return usuario


@app.get("/equipe/empresa", response_model=schemas.EmpresaSaida)
def minha_empresa(db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    return db.query(models.Empresa).filter(models.Empresa.id == usuario.empresa_id).first()


@app.get("/equipe/membros", response_model=list[schemas.MembroEquipeSaida])
def listar_membros(db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    return db.query(models.User).filter(models.User.empresa_id == usuario.empresa_id).all()


@app.post("/equipe/convidar", response_model=schemas.ConviteSaida, status_code=201)
def convidar_membro(
    dados: schemas.ConvidarEntrada,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(exigir_owner),
):
    """Só o owner pode convidar. Retorna um token — envie o link de cadastro
    (ex: https://seusite.com/cadastro?convite=TOKEN) manualmente por enquanto
    (envio automático de e-mail fica pra uma fase futura)."""
    convite = models.ConviteEquipe(empresa_id=usuario.empresa_id, email_convidado=dados.email)
    db.add(convite)
    db.commit()
    db.refresh(convite)
    return convite


# ============================================================
# Critérios (agora compartilhados pela empresa/equipe toda)
# ============================================================

@app.get("/criterios", response_model=list[schemas.CriterioSaida])
def listar_criterios(db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    return db.query(models.Criterio).filter(models.Criterio.empresa_id == usuario.empresa_id).all()


@app.post("/criterios", response_model=schemas.CriterioSaida, status_code=201)
def criar_criterio(
    dados: schemas.CriterioCriar,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    criterio = models.Criterio(**dados.model_dump(), empresa_id=usuario.empresa_id)
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
        models.Criterio.id == criterio_id, models.Criterio.empresa_id == usuario.empresa_id
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
        models.Criterio.id == criterio_id, models.Criterio.empresa_id == usuario.empresa_id
    ).first()
    if not criterio:
        raise HTTPException(status_code=404, detail="Critério não encontrado")
    db.delete(criterio)
    db.commit()


# ============================================================
# Licitações — filtro por critério + busca avançada (as duas combinam)
# ============================================================

@app.get("/licitacoes", response_model=schemas.LicitacoesPaginadas)
def listar_licitacoes(
    criterio_id: int | None = None,
    busca: str | None = None,
    uf: str | None = None,
    orgao: str | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    data_de: str | None = None,
    data_ate: str | None = None,
    pagina: int = 1,
    por_pagina: int = 30,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    """
    Três formas de usar, que se combinam:
    - Só `criterio_id` (ou nenhum parâmetro): aplica os critérios salvos da
      empresa ("Licitações pra você").
    - Só `busca`/filtros soltos, sem critério: busca livre em TODAS as
      licitações ativas — Brasil inteiro, qualquer modalidade — sem
      precisar de critério salvo.
    - `criterio_id` + `busca`/filtros: primeiro aplica o critério, depois
      refina o resultado com os filtros soltos.

    O filtro pesado (texto, valor, estado, órgão) roda direto no banco
    (SQL) antes de qualquer processamento em Python — isso é o que mantém
    a busca rápida mesmo com uma base nacional bem maior.

    Resultado vem paginado (`pagina`, começando em 1; `por_pagina`,
    padrão 30) — importante com uma base grande, pra não devolver
    milhares de itens numa resposta só.
    """
    pagina = max(1, pagina)
    por_pagina = max(1, min(por_pagina, 200))  # trava um teto, pra ninguém pedir 100000 de uma vez

    tem_filtro_avancado = any([busca, uf, orgao, valor_min is not None, valor_max is not None, data_de, data_ate])

    # -------- Pré-filtro no banco (rápido, mesmo com muitos registros) --------
    query = db.query(models.Licitacao).filter(models.Licitacao.ativa == True)  # noqa: E712

    if busca:
        query = query.filter(models.Licitacao.texto_busca.contains(scoring.normalizar(busca)))
    if uf:
        query = query.filter(models.Licitacao.uf == uf.upper())
    if orgao:
        query = query.filter(models.Licitacao.orgao.ilike(f"%{orgao}%"))
    if valor_min is not None:
        query = query.filter(models.Licitacao.valor_estimado >= valor_min)
    if valor_max is not None:
        query = query.filter(models.Licitacao.valor_estimado <= valor_max)
    if data_de:
        query = query.filter(models.Licitacao.data_encerramento_proposta >= data_de)
    if data_ate:
        query = query.filter(models.Licitacao.data_encerramento_proposta <= data_ate + "T23:59:59")

    candidatas = query.all()

    favoritos_ids = {
        f.numero_controle for f in
        db.query(models.Favorito).filter(models.Favorito.user_id == usuario.id).all()
    }

    resultados = {}

    if criterio_id is not None or (criterio_id is None and not tem_filtro_avancado):
        # Modo "critérios salvos" ("Licitações pra você")
        query_criterios = db.query(models.Criterio).filter(
            models.Criterio.empresa_id == usuario.empresa_id, models.Criterio.ativo == True  # noqa: E712
        )
        if criterio_id is not None:
            query_criterios = query_criterios.filter(models.Criterio.id == criterio_id)
        criterios = query_criterios.all()

        for licitacao in candidatas:
            melhor_score, melhores_motivos, passou_algum = 0, [], False
            for criterio in criterios:
                passou, motivos, score = scoring.aplicar_criterio(licitacao, criterio)
                if passou and score > melhor_score:
                    passou_algum, melhor_score, melhores_motivos = True, score, motivos

            if passou_algum:
                saida = schemas.LicitacaoSaida.model_validate(licitacao)
                saida.score = melhor_score
                saida.motivos = melhores_motivos
                saida.favoritada = licitacao.numero_controle in favoritos_ids
                resultados[licitacao.numero_controle] = saida
    else:
        # Modo "busca livre" — sem critério, Brasil inteiro, qualquer modalidade
        for licitacao in candidatas:
            saida = schemas.LicitacaoSaida.model_validate(licitacao)
            saida.score = 0
            saida.motivos = ["Busca livre"]
            saida.favoritada = licitacao.numero_controle in favoritos_ids
            resultados[licitacao.numero_controle] = saida

    todos_ordenados = sorted(resultados.values(), key=lambda r: r.score, reverse=True)

    total = len(todos_ordenados)
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    inicio = (pagina - 1) * por_pagina
    pagina_de_itens = todos_ordenados[inicio:inicio + por_pagina]

    return schemas.LicitacoesPaginadas(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas,
        itens=pagina_de_itens,
    )


# ============================================================
# Favoritos
# ============================================================

@app.post("/favoritos", status_code=201)
def favoritar(dados: schemas.FavoritoCriar, db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    licitacao = db.query(models.Licitacao).filter(models.Licitacao.numero_controle == dados.numero_controle).first()
    if not licitacao:
        raise HTTPException(status_code=404, detail="Licitação não encontrada")

    ja_existe = db.query(models.Favorito).filter(
        models.Favorito.user_id == usuario.id, models.Favorito.numero_controle == dados.numero_controle
    ).first()
    if ja_existe:
        return {"ok": True, "ja_era_favorito": True}

    db.add(models.Favorito(user_id=usuario.id, numero_controle=dados.numero_controle))
    db.commit()
    return {"ok": True}


@app.delete("/favoritos", status_code=204)
def desfavoritar(numero_controle: str, db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    fav = db.query(models.Favorito).filter(
        models.Favorito.user_id == usuario.id, models.Favorito.numero_controle == numero_controle
    ).first()
    if fav:
        db.delete(fav)
        db.commit()


@app.get("/favoritos", response_model=list[schemas.LicitacaoSaida])
def listar_favoritos(db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    favoritos = db.query(models.Favorito).filter(models.Favorito.user_id == usuario.id).all()
    resultado = []
    for fav in favoritos:
        licitacao = db.query(models.Licitacao).filter(models.Licitacao.numero_controle == fav.numero_controle).first()
        if licitacao:
            saida = schemas.LicitacaoSaida.model_validate(licitacao)
            saida.favoritada = True
            resultado.append(saida)
    return resultado


# ============================================================
# Comentários
# ============================================================

@app.get("/comentarios", response_model=list[schemas.ComentarioSaida])
def listar_comentarios(numero_controle: str, db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    comentarios = db.query(models.Comentario).filter(
        models.Comentario.numero_controle == numero_controle
    ).order_by(models.Comentario.criado_em.desc()).all()

    saida = []
    for c in comentarios:
        item = schemas.ComentarioSaida.model_validate(c)
        item.autor_email = c.usuario.email
        saida.append(item)
    return saida


@app.post("/comentarios", response_model=schemas.ComentarioSaida, status_code=201)
def criar_comentario(
    dados: schemas.ComentarioCriar,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    licitacao = db.query(models.Licitacao).filter(models.Licitacao.numero_controle == dados.numero_controle).first()
    if not licitacao:
        raise HTTPException(status_code=404, detail="Licitação não encontrada")

    comentario = models.Comentario(user_id=usuario.id, numero_controle=dados.numero_controle, texto=dados.texto)
    db.add(comentario)
    db.commit()
    db.refresh(comentario)

    saida = schemas.ComentarioSaida.model_validate(comentario)
    saida.autor_email = usuario.email
    return saida


@app.get("/")
def raiz():
    return {"status": "ok", "mensagem": "API do Buscador de Licitações no ar. Veja /docs"}