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

## 3. Popular a base com licitações (seed inicial)

O coletor (`collector_pncp.py`) não roda sozinho no Render — assim como
localmente, ele precisa ser executado (o agendamento automático fica por
sua conta: ver seção 5). Pra ter dados na primeira vez que abrir a URL:

1. No serviço `licittracker-backend`, abra a aba **Shell**.
2. Rode:
   ```bash
   python collector_pncp.py
   ```
3. Isso coleta o Brasil inteiro pra várias modalidades — pode levar bastante
   tempo (o próprio script avisa: "rodar de madrugada ajuda"). Se quiser um
   teste mais rápido pra confirmar que está tudo funcionando antes de rodar
   a coleta completa, edite temporariamente `MODALIDADES` no topo do
   script pra deixar só uma modalidade descomentada, rode, confira que
   apareceu no site, e depois rode de novo com todas.

## 4. Limitação importante: disco efêmero no plano free

O backend usa SQLite (arquivo local) por padrão. No plano free do Render, o
disco **não é persistente entre deploys** — cada novo deploy começa com o
banco vazio de novo (é preciso rodar o coletor de novo depois). Restart por
inatividade (o serviço "dorme" e acorda sozinho) não apaga o disco, só um
deploy novo apaga.

Isso é aceitável pra uma demo de portfólio, mas se quiser persistência de
verdade (dados sobrevivendo a redeploys), a forma mais simples é trocar
pra Postgres — o projeto já foi desenhado pra isso
(`backend/app/database.py`): basta criar um banco Postgres gratuito (ex:
[Neon](https://neon.tech) ou o Postgres do próprio Render), adicionar
`psycopg[binary]` em `backend/requirements.txt`, e definir a variável de
ambiente `DATABASE_URL` do serviço backend com a connection string do
Postgres — nenhum outro código muda.

## 5. Coleta diária automática (opcional)

Localmente isso é feito pelo Agendador de Tarefas do Windows
(`rodar_coletor_diario.bat`). No Render, a forma equivalente é um **Cron
Job** (**New** → **Cron Job**, mesmo Root Directory/Build Command do
backend, Start Command `python collector_pncp.py`, schedule ex: `0 6 * * *`
pra rodar 06:00 UTC todo dia). Só funciona corretamente se o backend já
estiver usando Postgres (seção 4) — com SQLite, o Cron Job roda num
container separado do backend e os dois não compartilham o mesmo arquivo de
banco, então o que ele coletar não apareceria no site.

## 6. Depois do deploy

Atualize a URL pública no `README.md` e no campo "Website" do repositório
no GitHub (**Settings** → topo da página, ícone de engrenagem ao lado de
"About").
