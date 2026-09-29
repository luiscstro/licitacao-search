# Deploy (backend na Discloud, frontend no Render)

O backend (FastAPI) roda na [Discloud](https://discloud.com) e o frontend
(estático) roda no [Render](https://render.com), usando o `render.yaml` da
raiz do repositório.

## 1. Por que o backend não fica no Render

Testando de verdade, descobri que **o PNCP recusa conexão (connection
timeout, não é rate limit) de requisições vindas dos servidores do
Render** — bloqueio de faixa de IP de provedor de nuvem, comum em órgãos
públicos brasileiros. Isso significa que **o coletor nunca funciona
rodando a partir do Render**, não importa como (endpoint admin, Shell,
Cron Job). O plano free do Render também tem cold-start de 20-50s depois
de ~15 min sem tráfego, deixando o primeiro acesso lento pra quem chega
depois de um tempo parado.

A Discloud (com plano Platinum, necessário pra `TYPE=site`) resolve os
dois problemas: o PNCP não bloqueia a faixa de IP dela, e não há
cold-start — confirmado ao vivo, coleta rodando normalmente e sem atraso
na primeira requisição.

## 2. Backend na Discloud

### 2.1. Pré-requisitos

- Conta na Discloud com plano que permita `TYPE=site` (Platinum).
- RAM livre suficiente na conta pro app (`backend/discloud.config` pede
  512MB — a RAM é compartilhada entre todos os apps da conta, então libere
  esse tanto se estiver perto do limite).

### 2.2. Arquivos do backend

Já existem no repositório, em `backend/`:

- **`discloud.config`** — `MAIN=run_discloud.py`, `TYPE=site`,
  `RAM=512`. A Discloud exige que o app escute em `0.0.0.0:8080`
  independente do framework.
- **`run_discloud.py`** — ponto de entrada que sobe o uvicorn nesse
  host/porta (`app/main.py` só define a instância do FastAPI, não sobe
  servidor sozinho).

### 2.3. Variáveis de ambiente

No painel da Discloud (ou via API), configure no app:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | connection string do Postgres (seção 3) |
| `SECRET_KEY` | valor aleatório: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_TOKEN` | valor aleatório: `python -c "import secrets; print(secrets.token_hex(24))"` |
| `COLETOR_MODALIDADES` | opcional — códigos separados por vírgula (ex: `6` só Pregão Eletrônico); sem essa variável, roda as 5 modalidades padrão |

**Duas pegadinhas da API da Discloud, descobertas na prática:**

1. `PUT /env/app/{appID}` **substitui todas as variáveis, não faz merge**
   — enviar só uma variável nova apaga as outras. Sempre reenvie o
   conjunto completo (`DATABASE_URL`, `SECRET_KEY`, `ADMIN_TOKEN`,
   `COLETOR_MODALIDADES`) junto.
2. `restart` e `stop`+`start` **não aplicam variáveis de ambiente novas**
   ao processo em execução — só um re-upload completo do código
   (`PUT /app/{appID}/commit`, ou o comando `discloud commit` da CLI)
   força o processo a subir de novo lendo as variáveis atualizadas.

### 2.4. Publicar

Com a [Discloud CLI](https://docs.discloud.com) autenticada, dentro de
`backend/`:

```bash
discloud commit
```

Isso reenvia o código completo e sobe o processo do zero (lendo as
variáveis de ambiente já configuradas no painel).

## 3. Postgres gratuito (Neon)

1. Crie uma conta em <https://neon.tech> (grátis, sem cartão).
2. **Create a project** → dê um nome (ex: `licittracker`) → crie.
3. Copie a **Connection string** (formato
   `postgresql://usuario:senha@host/banco?sslmode=require`) e use como
   `DATABASE_URL` (seção 2.3). Na inicialização, o backend cria as tabelas
   sozinho nesse Postgres.

## 4. Frontend no Render

1. No dashboard do Render, **New** → **Blueprint**, selecione o
   repositório `licitacao-search`. O Render lê o `render.yaml` da raiz e
   cria o serviço `licittracker-frontend` (site estático), já com
   `VITE_API_BASE` apontando pro backend na Discloud.
2. Se preferir configurar manualmente (**New** → **Static Site**):

   | Campo | Valor |
   |---|---|
   | Root Directory | `frontend` |
   | Build Command | `npm install && npm run build` |
   | Publish Directory | `dist` |
   | Variável `VITE_API_BASE` | `https://licittraker.discloud.dev` (ou o domínio real do seu app na Discloud) |

## 5. Coletar dados

Como a Discloud não é bloqueada pelo PNCP, o endpoint admin funciona
hospedado lá — não precisa mais rodar o coletor localmente nem depender só
do GitHub Actions:

```bash
curl -X POST https://licittraker.discloud.dev/admin/coletar-pncp -H "x-admin-token: SEU_ADMIN_TOKEN"
curl https://licittraker.discloud.dev/admin/coletar-pncp/status -H "x-admin-token: SEU_ADMIN_TOKEN"
```

Por padrão o coletor busca 5 modalidades, Brasil inteiro — leva **várias
horas** (o PNCP aplica rate limit com frequência). Pra um seed mais
rápido, defina `COLETOR_MODALIDADES` (seção 2.3) antes de disparar.

### Coleta periódica automática

Duas opções, ambas funcionam (nenhuma depende de máquina local ligada):

- **GitHub Actions** (`.github/workflows/coletor-pncp.yml`) — já está no
  repositório, roda diariamente (06:00 UTC / 03:00 BRT) contra o mesmo
  `DATABASE_URL` (configurado como secret do repositório). Continua
  válido como está.
- **Chamar o endpoint admin da Discloud num agendamento externo** (ex.
  [cron-job.org](https://cron-job.org), gratuito) apontando pro
  `POST /admin/coletar-pncp` acima — alternativa mais simples, já que
  agora o próprio backend consegue coletar sem bloqueio.

## 6. Depois do deploy

Atualize a URL pública no `README.md` e no campo "Website" do repositório
no GitHub (**Settings** → topo da página, ícone de engrenagem ao lado de
"About") com a URL do frontend no Render.
