# Deploy (Render)

Passo a passo pra publicar o backend e o frontend gratuitamente no
[Render](https://render.com), usando o `render.yaml` da raiz do repositório.

## 1. Pré-requisitos

- O repositório já precisa estar no GitHub (com `main` atualizado).
- Uma conta no Render — crie em <https://dashboard.render.com/register>,
  entrando com a sua conta do GitHub (mais rápido: já autoriza o Render a
  ler seus repositórios).

## 2. Criar os serviços via Blueprint

1. No dashboard do Render, clique em **New** → **Blueprint**.
2. Selecione o repositório `licitacao-search`.
3. O Render lê o `render.yaml` da raiz e mostra os dois serviços que vai
   criar: `licittracker-backend` (web service Python) e
   `licittracker-frontend` (site estático). Confirme com **Apply**.
4. Aguarde os dois builds terminarem (o do backend demora mais — instala
   `cryptography`/`bcrypt`, alguns minutos na primeira vez).
5. Quando terminar, cada serviço mostra sua URL pública, algo como:
   - Backend: `https://licittracker-backend.onrender.com`
   - Frontend: `https://licittracker-frontend.onrender.com`

Se o Render tiver sufixado algum nome (porque já estava em uso por outra
conta), o `VITE_API_BASE` do frontend vai continuar apontando pro nome
antigo — edite a variável de ambiente do serviço `licittracker-frontend`
(**Environment** → `VITE_API_BASE`) pra URL real do backend e clique em
**Manual Deploy** → **Deploy latest commit** pra rebuildar com o valor
certo.

### Se o Blueprint falhar ou você preferir configurar manualmente

Backend (**New** → **Web Service**, conecte o repo):

| Campo | Valor |
|---|---|
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Variável `SECRET_KEY` | gere um valor aleatório (ex: `python -c "import secrets; print(secrets.token_hex(32))"`) |

Frontend (**New** → **Static Site**, conecte o repo):

| Campo | Valor |
|---|---|
| Root Directory | `frontend` |
| Build Command | `npm install && npm run build` |
| Publish Directory | `dist` |
| Variável `VITE_API_BASE` | a URL pública do backend (do passo anterior) |

## 3. IMPORTANTE: o PNCP bloqueia conexões saindo do Render

Testando de verdade, descobri que **o PNCP recusa conexão (connection
timeout, não é rate limit) de requisições vindas dos servidores do
Render** — provavelmente bloqueio de faixa de IP de provedor de nuvem,
comum em órgãos públicos brasileiros. Isso significa que **o coletor nunca
vai funcionar rodando a partir do Render**, não importa como (endpoint
admin, Shell, Cron Job) — o problema é de rede, não de código, e nenhuma
dessas formas de disparo resolve.

O endpoint `POST /admin/coletar-pncp` (seção 4) continua existindo e pode
funcionar em outro provedor que o PNCP não bloqueie, mas **no Render,
especificamente, não use ele pra coletar** — só serve pra outros ambientes.

A solução: usar Postgres (acessível pela rede) em vez de SQLite (arquivo
local), e rodar o coletor **na sua própria máquina** (que consegue falar
com o PNCP normalmente — testado, funciona) apontando pro mesmo Postgres
que o backend publicado usa. O backend nunca precisa falar com o PNCP
diretamente; só lê do banco.

### 3.1. Criar um Postgres gratuito (Neon)

1. Crie uma conta em <https://neon.tech> (grátis, sem cartão).
2. **Create a project** → dê um nome (ex: `licittracker`) → crie.
3. Copie a **Connection string** que o Neon mostra (formato
   `postgresql://usuario:senha@host/banco?sslmode=require`).

### 3.2. Apontar o backend do Render pra esse Postgres

1. No serviço `licittracker-backend` → **Environment** → **Add Environment
   Variable**.
2. `DATABASE_URL` = a connection string do Neon (cole exatamente como o
   Neon deu).
3. Salve — isso redeploya o serviço automaticamente. Na inicialização, o
   backend cria as tabelas sozinho nesse Postgres (mesmo mecanismo que já
   usa pro SQLite).

### 3.3. Rodar o coletor localmente, escrevendo nesse Postgres

Na sua máquina (não no Render):

```bash
cd backend
# Windows (PowerShell):
$env:DATABASE_URL = "postgresql://usuario:senha@host/banco?sslmode=require"
python collector_pncp.py
```

Isso roda a coleta local (que já funciona) escrevendo direto no banco que
o site publicado lê. Repita sempre que quiser atualizar os dados — não
precisa redeployar nada no Render pra isso.

Pra uma coleta mais rápida (só uma modalidade em vez de 5), defina também
`COLETOR_MODALIDADES` antes de rodar — ex. no PowerShell:
`$env:COLETOR_MODALIDADES = "6"` (só "Pregão - Eletrônico"; sem essa
variável, roda todas). Veja a seção 5.

## 4. Endpoint admin (`POST /admin/coletar-pncp`)

Existe pra disparar o coletor por HTTP em ambientes sem acesso a Shell —
mas **não funciona no Render** pelo motivo da seção 3 (o PNCP bloqueia
esse provedor). Documentado aqui só pra quem hospedar o backend em outro
lugar que o PNCP não bloqueie:

1. Copie o valor de `ADMIN_TOKEN` em **Environment** (o Render gera
   automaticamente, via `generateValue` no `render.yaml` — se o serviço já
   existia antes dessa variável ser adicionada, gere um valor você mesmo:
   `python -c "import secrets; print(secrets.token_hex(24))"`).
2. `curl -X POST https://SEU-BACKEND/admin/coletar-pncp -H "x-admin-token: SEU_ADMIN_TOKEN"`
   — resposta `202` confirma que começou em background.
3. Status: `curl https://SEU-BACKEND/admin/coletar-pncp/status -H "x-admin-token: SEU_ADMIN_TOKEN"`.

## 5. Restringir modalidades pra um seed mais rápido

Por padrão o coletor busca 5 modalidades, Brasil inteiro — na prática isso
leva **várias horas** (o PNCP aplica rate limit com frequência; testado ao
vivo: só a modalidade "Pregão Eletrônico" sozinha já passou de 30 minutos).
Defina a variável de ambiente `COLETOR_MODALIDADES` (códigos separados por
vírgula, ex: `6` ou `6,7`) antes de rodar `collector_pncp.py` — funciona
tanto localmente quanto no Render (se um dia o bloqueio da seção 3 não se
aplicar mais). Sem essa variável, roda as 5 modalidades padrão.

## 6. Disco efêmero (SQLite) vs. Postgres

Se você pulou a seção 3 e continua no SQLite padrão: no plano free do
Render, o disco **não é persistente entre deploys** — cada novo deploy
zera o banco. Com Postgres (seção 3), isso deixa de ser problema — os
dados sobrevivem a qualquer redeploy, porque vivem fora do container.

## 7. Coleta periódica automática (GitHub Actions)

O coletor não pode rodar no Render (seção 3), mas **não precisa da sua
máquina ligada** — o workflow `.github/workflows/coletor-pncp.yml` já
está no repositório e roda num agendamento diário (06:00 UTC / 03:00
BRT) direto no GitHub Actions, que testamos e o PNCP não bloqueia
(infraestrutura diferente do Render).

Pra ativar:

1. No repositório do GitHub → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**.
2. Nome: `DATABASE_URL`. Valor: a mesma connection string do Neon usada no
   Render (seção 3).
3. Pronto — o workflow já roda sozinho todo dia. Pra rodar uma vez agora
   (sem esperar o horário agendado), vá em **Actions** → **Coletor de
   licitações do PNCP** → **Run workflow**.

Opcional: pra restringir a coleta a modalidades específicas (mais rápido,
ver seção 5), adicione uma **Repository variable** (mesma tela, aba
"Variables") chamada `COLETOR_MODALIDADES` com o valor desejado (ex: `6`).

Isso substitui completamente a necessidade de rodar `collector_pncp.py`
manualmente ou via Agendador de Tarefas do Windows — mas esse caminho
local continua funcionando (seção 3.3) se você preferir, ou quiser rodar
uma coleta pontual sem esperar o agendamento.

## 8. Depois do deploy

Atualize a URL pública no `README.md` e no campo "Website" do repositório
no GitHub (**Settings** → topo da página, ícone de engrenagem ao lado de
"About").
