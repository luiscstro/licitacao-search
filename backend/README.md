# Buscador de Licitações — Fase 3 (Backend com API e login)

Essa é a base do produto de verdade: agora existe **login**, e cada
cliente configura seus **próprios critérios**, todos rodando sobre uma
única base de licitações coletadas do PNCP.

## Estrutura da pasta

```
backend/
├── app/
│   ├── __init__.py
│   ├── database.py      <- conexão com o banco (SQLite por padrão)
│   ├── models.py        <- tabelas: usuários, critérios, licitações
│   ├── schemas.py        <- formato dos dados de entrada/saída da API
│   ├── auth.py            <- login, senha, token JWT
│   ├── scoring.py          <- lógica de filtro/pontuação por critério
│   └── main.py              <- a API em si (todos os endpoints)
├── collector_pncp.py           <- coletor (roda 1x/dia, agendado)
└── requirements.txt
```

## Passo 1 — Instalar dependências

Dentro da pasta `backend`:

```
pip install -r requirements.txt
```

## Passo 2 — Rodar a API

```
uvicorn app.main:app --reload
```

Abra **http://127.0.0.1:8000/docs** no navegador. Isso abre uma interface
interativa (gerada automaticamente pelo FastAPI) onde você pode testar
TODOS os endpoints sem precisar de frontend nenhum ainda — cadastro,
login, criar critério, listar licitações etc.

## Passo 3 — Rodar o coletor

Numa outra janela de terminal (deixa a API rodando na primeira):

```
python collector_pncp.py
```

Isso vai popular a tabela `licitacoes` com os pregões do PNCP. Igual nas
fases anteriores, pode ser agendado pra rodar sozinho todo dia de
madrugada (reaproveite a lógica do `rodar_diario.bat` da Fase 2, só
apontando pro `collector_pncp.py` novo).

## Testando o fluxo completo pelo /docs

1. Abra `/docs`
2. Em **POST /auth/registrar**, clique "Try it out", preencha email/senha, execute
3. Em **POST /auth/login**, faça login com o mesmo email/senha — copie o `access_token` que voltar
4. No topo da página, clique no botão **"Authorize"** (cadeado) e cole o token
5. Agora todos os endpoints protegidos (críticos, licitações) vão funcionar autenticados
6. Em **POST /criterios**, crie um critério com seus filtros
7. Em **GET /licitacoes**, veja as licitações que batem com esse critério

## O que já funciona (testado)

- Cadastro e login com senha protegida (hash bcrypt, nunca texto puro)
- Autenticação por token JWT (expira em 7 dias)
- Cada cliente só vê e edita os próprios critérios (isolamento entre contas)
- Um cliente pode ter vários critérios ao mesmo tempo (ex: dois nichos diferentes)
- A busca de licitações aplica os critérios do cliente logado sobre a base
  compartilhada — sem duplicar coleta de dados por cliente

## Segurança — ajustar antes de ir pra produção

- **SECRET_KEY**: hoje tem um valor fixo de exemplo em `auth.py`. Antes de
  publicar de verdade, defina a variável de ambiente `SECRET_KEY` com um
  valor aleatório e secreto (ex: gerado com `python -c "import secrets; print(secrets.token_hex(32))"`)
- **CORS**: em `main.py`, `allow_origins=["*"]` libera qualquer site a
  chamar sua API. Quando tiver o frontend publicado, troque pela URL real
  dele.
- **Banco de dados**: SQLite é ótimo pra desenvolver e validar, mas pra um
  produto com clientes pagantes de verdade, o recomendado é migrar pra
  PostgreSQL (só trocar a variável `DATABASE_URL`, o resto do código não muda).

## Próxima fase

Com a API funcionando, a Fase 4 é o **frontend** — a telinha de verdade
que seus clientes vão usar (cadastro, configurar critérios visualmente,
ver o dashboard de licitações) — hoje eles só conseguem usar via `/docs`,
que é ótimo pra testar mas não é o que você vai vender.