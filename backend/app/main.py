"""
API principal — Buscador de Licitações (SaaS)

Pra rodar localmente:
    uvicorn app.main:app --reload

Depois abra http://127.0.0.1:8000/docs
"""

import io
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import auth, cnpj_utils, exportacao, models, schemas, scoring
from .database import Base, engine, get_db
from .observability import setup_observability

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Buscador de Licitações API", version="2.0")
setup_observability(app)

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
        convite = (
            db.query(models.ConviteEquipe)
            .filter(
                models.ConviteEquipe.token == dados.token_convite,
                models.ConviteEquipe.usado == False,  # noqa: E712
            )
            .first()
        )
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


@app.put("/auth/preferencias", response_model=schemas.UsuarioSaida)
def atualizar_preferencias(
    dados: schemas.PreferenciasAtualizar,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario


@app.get("/equipe/empresa", response_model=schemas.EmpresaSaida)
def minha_empresa(db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    return db.query(models.Empresa).filter(models.Empresa.id == usuario.empresa_id).first()


@app.put("/equipe/empresa", response_model=schemas.EmpresaSaida)
def atualizar_empresa(
    dados: schemas.EmpresaAtualizar,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(exigir_owner),
):
    empresa = db.query(models.Empresa).filter(models.Empresa.id == usuario.empresa_id).first()
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(empresa, campo, valor)
    db.commit()
    db.refresh(empresa)
    return empresa


@app.post("/equipe/empresa/sincronizar-cnpj", response_model=schemas.EmpresaSaida)
def sincronizar_cnpj(
    db: Session = Depends(get_db),
    usuario: models.User = Depends(exigir_owner),
):
    """Busca dados cadastrais via APIs públicas de dados abertos do CNPJ
    (BrasilAPI, com fallback pra MinhaReceita) — sem login, sem CAPTCHA.
    Só preenche os campos de endereço que estiverem vazios, pra não
    sobrescrever edição manual do usuário; situação cadastral sempre
    atualiza."""
    empresa = db.query(models.Empresa).filter(models.Empresa.id == usuario.empresa_id).first()
    if not empresa.cnpj:
        raise HTTPException(status_code=400, detail="Cadastre o CNPJ da empresa antes de sincronizar")

    try:
        dados = cnpj_utils.buscar_dados_cnpj(empresa.cnpj)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))

    if dados is None:
        raise HTTPException(
            status_code=502, detail="Não foi possível consultar o CNPJ agora — tente de novo em instantes"
        )

    empresa.situacao_cadastral = dados["situacao_cadastral"]
    empresa.cnpj_sincronizado_em = datetime.utcnow()
    if not empresa.nome and dados.get("razao_social"):
        empresa.nome = dados["razao_social"]
    for campo in [
        "endereco_logradouro",
        "endereco_numero",
        "endereco_complemento",
        "endereco_bairro",
        "endereco_cidade",
        "endereco_uf",
        "endereco_cep",
    ]:
        if not getattr(empresa, campo) and dados.get(campo):
            setattr(empresa, campo, dados[campo])

    db.commit()
    db.refresh(empresa)
    return empresa


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
    criterio = (
        db.query(models.Criterio)
        .filter(models.Criterio.id == criterio_id, models.Criterio.empresa_id == usuario.empresa_id)
        .first()
    )
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
    criterio = (
        db.query(models.Criterio)
        .filter(models.Criterio.id == criterio_id, models.Criterio.empresa_id == usuario.empresa_id)
        .first()
    )
    if not criterio:
        raise HTTPException(status_code=404, detail="Critério não encontrado")
    db.delete(criterio)
    db.commit()


# ============================================================
# Licitações — filtro por critério + busca avançada (as duas combinam)
# ============================================================


def _buscar_licitacoes_pontuadas(
    db: Session,
    usuario: models.User,
    criterio_id: int | None,
    busca: str | None,
    uf: str | None,
    orgao: str | None,
    valor_min: float | None,
    valor_max: float | None,
    data_de: str | None,
    data_ate: str | None,
    uasg: str | None = None,
    numero_pregao: str | None = None,
) -> list[schemas.LicitacaoSaida]:
    """
    Núcleo compartilhado de busca/pontuação — usado por `/licitacoes`,
    `/licitacoes/exportar` e `/licitacoes/estatisticas`. Devolve a lista
    JÁ ordenada por pontuação (sem paginar).

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
    """
    tem_filtro_avancado = any(
        [
            busca,
            uf,
            orgao,
            valor_min is not None,
            valor_max is not None,
            data_de,
            data_ate,
            uasg,
            numero_pregao,
        ]
    )

    # -------- Pré-filtro no banco (rápido, mesmo com muitos registros) --------
    query = db.query(models.Licitacao).filter(models.Licitacao.ativa == True)  # noqa: E712

    if busca:
        query = query.filter(models.Licitacao.texto_busca.contains(scoring.normalizar(busca)))
    if uf:
        query = query.filter(models.Licitacao.uf == uf.upper())
    if orgao:
        query = query.filter(models.Licitacao.orgao.ilike(f"%{orgao}%"))
    if uasg:
        query = query.filter(models.Licitacao.codigo_unidade == uasg.strip())
    if numero_pregao:
        query = query.filter(models.Licitacao.numero_compra.ilike(f"%{numero_pregao.strip()}%"))
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
        f.numero_controle
        for f in db.query(models.Favorito).filter(models.Favorito.user_id == usuario.id).all()
    }

    resultados = {}

    if criterio_id is not None or (criterio_id is None and not tem_filtro_avancado):
        # Modo "critérios salvos" ("Licitações pra você")
        query_criterios = db.query(models.Criterio).filter(
            models.Criterio.empresa_id == usuario.empresa_id,
            models.Criterio.ativo == True,  # noqa: E712
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

    return sorted(resultados.values(), key=lambda r: r.score, reverse=True)


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
    uasg: str | None = None,
    numero_pregao: str | None = None,
    pagina: int = 1,
    por_pagina: int = 30,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    """Resultado vem paginado (`pagina`, começando em 1; `por_pagina`,
    padrão 30) — importante com uma base grande, pra não devolver
    milhares de itens numa resposta só."""
    pagina = max(1, pagina)
    por_pagina = max(1, min(por_pagina, 200))  # trava um teto, pra ninguém pedir 100000 de uma vez

    todos_ordenados = _buscar_licitacoes_pontuadas(
        db,
        usuario,
        criterio_id,
        busca,
        uf,
        orgao,
        valor_min,
        valor_max,
        data_de,
        data_ate,
        uasg,
        numero_pregao,
    )

    total = len(todos_ordenados)
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    inicio = (pagina - 1) * por_pagina
    pagina_de_itens = todos_ordenados[inicio : inicio + por_pagina]

    return schemas.LicitacoesPaginadas(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas,
        itens=pagina_de_itens,
    )


LIMITE_EXPORTACAO = 3000

MEDIA_TYPES_EXPORTACAO = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


@app.get("/licitacoes/exportar")
def exportar_licitacoes(
    formato: str = "csv",
    criterio_id: int | None = None,
    busca: str | None = None,
    uf: str | None = None,
    orgao: str | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    data_de: str | None = None,
    data_ate: str | None = None,
    uasg: str | None = None,
    numero_pregao: str | None = None,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    """Exporta o mesmo resultado de `/licitacoes` (mesmos filtros), sem
    paginação, num arquivo pra download. Limitado a LIMITE_EXPORTACAO itens
    pra não travar em buscas nacionais gigantes — refine os filtros se
    precisar de mais."""
    if formato not in MEDIA_TYPES_EXPORTACAO:
        raise HTTPException(status_code=400, detail="Formato inválido. Use csv, xlsx ou pdf.")

    itens = _buscar_licitacoes_pontuadas(
        db,
        usuario,
        criterio_id,
        busca,
        uf,
        orgao,
        valor_min,
        valor_max,
        data_de,
        data_ate,
        uasg,
        numero_pregao,
    )[:LIMITE_EXPORTACAO]

    if formato == "csv":
        conteudo = exportacao.gerar_csv(itens)
    elif formato == "xlsx":
        conteudo = exportacao.gerar_xlsx(itens)
    else:
        conteudo = exportacao.gerar_pdf(itens)

    nome_arquivo = f"licitacoes.{formato}"
    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type=MEDIA_TYPES_EXPORTACAO[formato],
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@app.get("/licitacoes/estatisticas", response_model=schemas.EstatisticasSaida)
def estatisticas_licitacoes(
    criterio_id: int | None = None,
    busca: str | None = None,
    uf: str | None = None,
    orgao: str | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    data_de: str | None = None,
    data_ate: str | None = None,
    uasg: str | None = None,
    numero_pregao: str | None = None,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    """Agregados (por UF, por modalidade, por mês) sobre o mesmo resultado
    de `/licitacoes`, pros gráficos do painel de indicadores."""
    itens = _buscar_licitacoes_pontuadas(
        db,
        usuario,
        criterio_id,
        busca,
        uf,
        orgao,
        valor_min,
        valor_max,
        data_de,
        data_ate,
        uasg,
        numero_pregao,
    )

    contagem_uf = Counter((i.uf or "Não informado") for i in itens)
    contagem_modalidade = Counter((i.modalidade or "Não informada") for i in itens)
    contagem_mes = Counter()
    for i in itens:
        data_ref = i.data_encerramento_proposta or ""
        contagem_mes[data_ref[:7] if len(data_ref) >= 7 else "Sem data"] += 1

    return schemas.EstatisticasSaida(
        total=len(itens),
        valor_total_estimado=sum(i.valor_estimado or 0 for i in itens),
        por_uf=[schemas.ContagemPorChave(chave=k, quantidade=v) for k, v in contagem_uf.most_common(15)],
        por_modalidade=[
            schemas.ContagemPorChave(chave=k, quantidade=v) for k, v in contagem_modalidade.most_common(10)
        ],
        por_mes=[schemas.ContagemPorChave(chave=k, quantidade=v) for k, v in sorted(contagem_mes.items())],
    )


# ============================================================
# Favoritos
# ============================================================


@app.post("/favoritos", status_code=201)
def favoritar(
    dados: schemas.FavoritoCriar,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    licitacao = (
        db.query(models.Licitacao).filter(models.Licitacao.numero_controle == dados.numero_controle).first()
    )
    if not licitacao:
        raise HTTPException(status_code=404, detail="Licitação não encontrada")

    ja_existe = (
        db.query(models.Favorito)
        .filter(
            models.Favorito.user_id == usuario.id, models.Favorito.numero_controle == dados.numero_controle
        )
        .first()
    )

    # Favoritar (por qualquer pessoa da empresa) coloca a licitação no
    # pipeline compartilhado, se ainda não estiver lá. Desfavoritar NÃO
    # tira do pipeline — ver DELETE /pipeline/{numero_controle}.
    ja_esta_no_pipeline = (
        db.query(models.Oportunidade)
        .filter(
            models.Oportunidade.empresa_id == usuario.empresa_id,
            models.Oportunidade.numero_controle == dados.numero_controle,
        )
        .first()
    )
    if not ja_esta_no_pipeline:
        db.add(models.Oportunidade(empresa_id=usuario.empresa_id, numero_controle=dados.numero_controle))

    if ja_existe:
        db.commit()
        return {"ok": True, "ja_era_favorito": True}

    db.add(models.Favorito(user_id=usuario.id, numero_controle=dados.numero_controle))
    db.commit()
    return {"ok": True}


@app.delete("/favoritos", status_code=204)
def desfavoritar(
    numero_controle: str, db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)
):
    fav = (
        db.query(models.Favorito)
        .filter(models.Favorito.user_id == usuario.id, models.Favorito.numero_controle == numero_controle)
        .first()
    )
    if fav:
        db.delete(fav)
        db.commit()


@app.get("/favoritos", response_model=list[schemas.LicitacaoSaida])
def listar_favoritos(db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    favoritos = db.query(models.Favorito).filter(models.Favorito.user_id == usuario.id).all()
    resultado = []
    for fav in favoritos:
        licitacao = (
            db.query(models.Licitacao).filter(models.Licitacao.numero_controle == fav.numero_controle).first()
        )
        if licitacao:
            saida = schemas.LicitacaoSaida.model_validate(licitacao)
            saida.favoritada = True
            resultado.append(saida)
    return resultado


# ============================================================
# Pipeline (mini-CRM, compartilhado pela empresa)
# ============================================================

STATUS_VALIDOS = ["monitorando", "analisando", "proposta_enviada", "ganhou", "perdeu"]


@app.get("/pipeline", response_model=list[schemas.OportunidadeSaida])
def listar_pipeline(db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    oportunidades = (
        db.query(models.Oportunidade).filter(models.Oportunidade.empresa_id == usuario.empresa_id).all()
    )

    resultado = []
    for oportunidade in oportunidades:
        licitacao = (
            db.query(models.Licitacao)
            .filter(models.Licitacao.numero_controle == oportunidade.numero_controle)
            .first()
        )
        if not licitacao:
            continue
        saida = schemas.OportunidadeSaida.model_validate(licitacao)
        saida.status = oportunidade.status
        saida.status_atualizado_em = oportunidade.status_atualizado_em
        saida.atualizado_por_email = oportunidade.atualizado_por.email if oportunidade.atualizado_por else ""
        resultado.append(saida)

    resultado.sort(key=lambda o: o.status_atualizado_em, reverse=True)
    return resultado


@app.put("/pipeline", response_model=schemas.OportunidadeSaida)
def atualizar_status_pipeline(
    numero_controle: str,
    dados: schemas.AtualizarStatusEntrada,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    if dados.status not in STATUS_VALIDOS:
        raise HTTPException(
            status_code=400, detail=f"Status inválido. Use um de: {', '.join(STATUS_VALIDOS)}"
        )

    oportunidade = (
        db.query(models.Oportunidade)
        .filter(
            models.Oportunidade.empresa_id == usuario.empresa_id,
            models.Oportunidade.numero_controle == numero_controle,
        )
        .first()
    )
    if not oportunidade:
        raise HTTPException(status_code=404, detail="Essa licitação não está no pipeline")

    oportunidade.status = dados.status
    oportunidade.status_atualizado_em = datetime.utcnow()
    oportunidade.atualizado_por_id = usuario.id
    db.commit()
    db.refresh(oportunidade)

    licitacao = db.query(models.Licitacao).filter(models.Licitacao.numero_controle == numero_controle).first()
    saida = schemas.OportunidadeSaida.model_validate(licitacao)
    saida.status = oportunidade.status
    saida.status_atualizado_em = oportunidade.status_atualizado_em
    saida.atualizado_por_email = usuario.email
    return saida


@app.delete("/pipeline", status_code=204)
def remover_do_pipeline(
    numero_controle: str,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    oportunidade = (
        db.query(models.Oportunidade)
        .filter(
            models.Oportunidade.empresa_id == usuario.empresa_id,
            models.Oportunidade.numero_controle == numero_controle,
        )
        .first()
    )
    if oportunidade:
        db.delete(oportunidade)
        db.commit()


# ============================================================
# Comentários
# ============================================================


@app.get("/comentarios", response_model=list[schemas.ComentarioSaida])
def listar_comentarios(
    numero_controle: str, db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)
):
    comentarios = (
        db.query(models.Comentario)
        .filter(models.Comentario.numero_controle == numero_controle)
        .order_by(models.Comentario.criado_em.desc())
        .all()
    )

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
    licitacao = (
        db.query(models.Licitacao).filter(models.Licitacao.numero_controle == dados.numero_controle).first()
    )
    if not licitacao:
        raise HTTPException(status_code=404, detail="Licitação não encontrada")

    comentario = models.Comentario(
        user_id=usuario.id, numero_controle=dados.numero_controle, texto=dados.texto
    )
    db.add(comentario)
    db.commit()
    db.refresh(comentario)

    saida = schemas.ComentarioSaida.model_validate(comentario)
    saida.autor_email = usuario.email
    return saida


# ============================================================
# Documentos de habilitação / certidões
# ============================================================

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
EXTENSOES_PERMITIDAS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
TAMANHO_MAXIMO_BYTES = 15 * 1024 * 1024


def _parse_data_opcional(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida, use o formato AAAA-MM-DD")


async def _salvar_arquivo(empresa_id: int, arquivo: UploadFile) -> tuple[str, str, int]:
    extensao = Path(arquivo.filename or "").suffix.lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensão não permitida. Use: {', '.join(sorted(EXTENSOES_PERMITIDAS))}",
        )

    conteudo = await arquivo.read()
    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo muito grande (máximo 15MB)")

    pasta_empresa = UPLOAD_DIR / str(empresa_id) / "documentos"
    pasta_empresa.mkdir(parents=True, exist_ok=True)
    nome_salvo = f"{uuid.uuid4().hex}{extensao}"
    caminho = pasta_empresa / nome_salvo
    caminho.write_bytes(conteudo)

    return str(caminho), (arquivo.filename or nome_salvo), len(conteudo)


def _serializar_documento(documento: models.DocumentoHabilitacao) -> schemas.DocumentoSaida:
    saida = schemas.DocumentoSaida.model_validate(documento)
    saida.status = documento.status
    saida.enviado_por_email = documento.enviado_por.email if documento.enviado_por else ""
    return saida


@app.get("/documentos/indicadores", response_model=schemas.IndicadoresDocumentosSaida)
def indicadores_documentos(db: Session = Depends(get_db), usuario: models.User = Depends(auth.usuario_atual)):
    documentos = (
        db.query(models.DocumentoHabilitacao)
        .filter(models.DocumentoHabilitacao.empresa_id == usuario.empresa_id)
        .all()
    )

    contagem_status = Counter(d.status for d in documentos)
    contagem_categoria = Counter(d.categoria for d in documentos)

    recentes = sorted(documentos, key=lambda d: d.atualizado_em, reverse=True)[:8]
    ultimas_atualizacoes = [
        schemas.AtividadeRecente(
            nome=d.nome,
            categoria=d.categoria,
            atualizado_em=d.atualizado_em,
            atualizado_por_email=d.enviado_por.email if d.enviado_por else "",
        )
        for d in recentes
    ]

    return schemas.IndicadoresDocumentosSaida(
        por_status=[schemas.ContagemPorStatus(status=k, quantidade=v) for k, v in contagem_status.items()],
        por_categoria=[
            schemas.ContagemPorChave(chave=k, quantidade=v) for k, v in contagem_categoria.items()
        ],
        ultimas_atualizacoes=ultimas_atualizacoes,
    )


@app.get("/documentos/historico", response_model=list[schemas.DocumentoHistoricoSaida])
def historico_documento(
    documento_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    query = db.query(models.DocumentoHistorico).filter(
        models.DocumentoHistorico.empresa_id == usuario.empresa_id
    )
    if documento_id is not None:
        query = query.filter(models.DocumentoHistorico.documento_id == documento_id)
    registros = query.order_by(models.DocumentoHistorico.substituido_em.desc()).all()

    saida = []
    for r in registros:
        item = schemas.DocumentoHistoricoSaida.model_validate(r)
        item.substituido_por_email = r.substituido_por.email if r.substituido_por else ""
        saida.append(item)
    return saida


@app.get("/documentos", response_model=list[schemas.DocumentoSaida])
def listar_documentos(
    categoria: str | None = None,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    query = db.query(models.DocumentoHabilitacao).filter(
        models.DocumentoHabilitacao.empresa_id == usuario.empresa_id
    )
    if categoria:
        query = query.filter(models.DocumentoHabilitacao.categoria == categoria)
    documentos = query.order_by(models.DocumentoHabilitacao.nome).all()
    return [_serializar_documento(d) for d in documentos]


@app.post("/documentos", response_model=schemas.DocumentoSaida, status_code=201)
async def criar_documento(
    file: UploadFile = File(...),
    categoria: str = Form(...),
    nome: str = Form(...),
    data_emissao: str | None = Form(None),
    data_validade: str | None = Form(None),
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    if categoria not in models.CATEGORIAS_DOCUMENTO:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria inválida. Use uma de: {', '.join(models.CATEGORIAS_DOCUMENTO)}",
        )

    caminho, nome_original, tamanho = await _salvar_arquivo(usuario.empresa_id, file)

    documento = models.DocumentoHabilitacao(
        empresa_id=usuario.empresa_id,
        categoria=categoria,
        nome=nome,
        nome_arquivo_original=nome_original,
        caminho_arquivo=caminho,
        tamanho_bytes=tamanho,
        data_emissao=_parse_data_opcional(data_emissao),
        data_validade=_parse_data_opcional(data_validade),
        enviado_por_id=usuario.id,
    )
    db.add(documento)
    db.commit()
    db.refresh(documento)
    return _serializar_documento(documento)


@app.put("/documentos/{documento_id}", response_model=schemas.DocumentoSaida)
def atualizar_documento(
    documento_id: int,
    dados: schemas.DocumentoAtualizar,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    documento = (
        db.query(models.DocumentoHabilitacao)
        .filter(
            models.DocumentoHabilitacao.id == documento_id,
            models.DocumentoHabilitacao.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    campos = dados.model_dump(exclude_unset=True)
    if "categoria" in campos and campos["categoria"] not in models.CATEGORIAS_DOCUMENTO:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria inválida. Use uma de: {', '.join(models.CATEGORIAS_DOCUMENTO)}",
        )
    for campo, valor in campos.items():
        setattr(documento, campo, valor)
    documento.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(documento)
    return _serializar_documento(documento)


@app.post("/documentos/{documento_id}/substituir", response_model=schemas.DocumentoSaida)
async def substituir_documento(
    documento_id: int,
    file: UploadFile = File(...),
    data_emissao: str | None = Form(None),
    data_validade: str | None = Form(None),
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    documento = (
        db.query(models.DocumentoHabilitacao)
        .filter(
            models.DocumentoHabilitacao.id == documento_id,
            models.DocumentoHabilitacao.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    db.add(
        models.DocumentoHistorico(
            empresa_id=usuario.empresa_id,
            documento_id=documento.id,
            nome=documento.nome,
            nome_arquivo_original=documento.nome_arquivo_original,
            caminho_arquivo=documento.caminho_arquivo,
            data_emissao=documento.data_emissao,
            data_validade=documento.data_validade,
            substituido_por_id=usuario.id,
        )
    )

    caminho, nome_original, tamanho = await _salvar_arquivo(usuario.empresa_id, file)
    documento.caminho_arquivo = caminho
    documento.nome_arquivo_original = nome_original
    documento.tamanho_bytes = tamanho
    if data_emissao is not None:
        documento.data_emissao = _parse_data_opcional(data_emissao)
    if data_validade is not None:
        documento.data_validade = _parse_data_opcional(data_validade)
    documento.enviado_por_id = usuario.id
    documento.ultimo_alerta_dias = None
    documento.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(documento)
    return _serializar_documento(documento)


@app.get("/documentos/{documento_id}/arquivo")
def baixar_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    documento = (
        db.query(models.DocumentoHabilitacao)
        .filter(
            models.DocumentoHabilitacao.id == documento_id,
            models.DocumentoHabilitacao.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not documento or not Path(documento.caminho_arquivo).exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(documento.caminho_arquivo, filename=documento.nome_arquivo_original)


@app.delete("/documentos/{documento_id}", status_code=204)
def remover_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    usuario: models.User = Depends(auth.usuario_atual),
):
    documento = (
        db.query(models.DocumentoHabilitacao)
        .filter(
            models.DocumentoHabilitacao.id == documento_id,
            models.DocumentoHabilitacao.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not documento:
        return
    caminho = Path(documento.caminho_arquivo)
    if caminho.exists():
        caminho.unlink()
    db.delete(documento)
    db.commit()


@app.get("/")
def raiz():
    return {"status": "ok", "mensagem": "API do Buscador de Licitações no ar. Veja /docs"}
