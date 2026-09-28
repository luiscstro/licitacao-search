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

O coletor (`collector_pncp.py`) não roda sozinho no Render — precisa ser
disparado manualmente (o agendamento automático fica por sua conta: ver
seção 5). A aba **Shell** do Render é recurso pago — o serviço já vem com
um jeito de disparar a coleta sem precisar dela: o endpoint
`POST /admin/coletar-pncp`.

1. No serviço `licittracker-backend`, abra **Environment** e copie o valor
   de `ADMIN_TOKEN` (o Render gera automaticamente, via `generateValue` no
   `render.yaml` — se o serviço já existia antes dessa variável ser
   adicionada, clique em **Add Environment Variable** e gere um valor você
   mesmo, ex: `python -c "import secrets; print(secrets.token_hex(24))"`).
2. Dispare a coleta com uma requisição POST (do seu navegador não dá,
   precisa ser POST — use `curl`, Postman, ou peça pra eu rodar por você
   se me passar a URL do backend e o token):
   ```bash
   curl -X POST https://licittracker-backend.onrender.com/admin/coletar-pncp \
     -H "x-admin-token: SEU_ADMIN_TOKEN_AQUI"
   ```
   A resposta (`202`) confirma que a coleta começou em segundo plano — a
   requisição não fica esperando ela terminar.
3. Acompanhe o progresso pelos **Logs** do serviço no Render, ou consultando:
   ```bash
   curl https://licittracker-backend.onrender.com/admin/coletar-pncp/status \
     -H "x-admin-token: SEU_ADMIN_TOKEN_AQUI"
   ```

Por padrão o coletor busca 5 modalidades, Brasil inteiro — na prática isso
leva **várias horas** (o PNCP aplica rate limit com frequência; testado ao
vivo: só a modalidade "Pregão Eletrônico" sozinha já passou de 30 minutos).
**Pra uma demo no ar rápido**, adicione a variável de ambiente
`COLETOR_MODALIDADES=6` no serviço `licittracker-backend` antes de disparar
a coleta — isso restringe a coleta só a "Pregão - Eletrônico" (a modalidade
mais comum, suficiente pra mostrar a plataforma funcionando de ponta a
ponta), sem precisar editar nenhum arquivo. Pra rodar mais de uma, separe
por vírgula (ex: `6,7`). Remova a variável (ou apague o valor) depois pra
voltar a coletar todas as modalidades nas próximas rodadas.

Se preferir a aba Shell (planos pagos), o comando é o mesmo de sempre:
`python collector_pncp.py` — a variável `COLETOR_MODALIDADES` funciona do
mesmo jeito nesse caminho também.

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
(`rodar_coletor_diario.bat`). No Render:

**Sem custo, usando o endpoint admin da seção 3**: qualquer serviço externo
de "ping agendado" funciona, já que é só uma chamada POST — ex:
[cron-job.org](https://cron-job.org) (grátis): cadastre uma URL
`https://licittracker-backend.onrender.com/admin/coletar-pncp`, método
`POST`, header `x-admin-token: SEU_ADMIN_TOKEN`, agendado pra uma vez por
dia. Como esse endpoint roda o coletor *dentro do mesmo serviço/processo*
do backend, ele compartilha o mesmo arquivo SQLite — funciona mesmo sem
Postgres (mas continua sujeito à limitação da seção 4: um redeploy zera a
base de novo).

**Com plano pago**: um **Cron Job** do Render (**New** → **Cron Job**,
mesmo Root Directory/Build Command do backend, Start Command
`python collector_pncp.py`, schedule ex: `0 6 * * *`) só funciona
corretamente se o backend já estiver usando Postgres (seção 4) — com
SQLite, o Cron Job roda num container separado do backend e os dois não
compartilham o mesmo arquivo de banco, então o que ele coletar não
apareceria no site.

## 6. Depois do deploy

Atualize a URL pública no `README.md` e no campo "Website" do repositório
no GitHub (**Settings** → topo da página, ícone de engrenagem ao lado de
"About").
