# Desenvolvimento — Backend

Ferramentas de qualidade e observabilidade do backend (FastAPI + SQLAlchemy).
Tudo aqui funciona 100% local, sem custo e sem precisar criar nenhuma conta
externa.

## Instalação

```bash
cd backend
pip install -r requirements-dev.txt   # já inclui requirements.txt via -r
```

## Lint e formatação (Ruff)

```bash
ruff check .        # lint
ruff check --fix .  # lint com autofix
ruff format .       # formatação
```

Config em `pyproject.toml` (`[tool.ruff]`). Regras ativas: `E`, `F`, `I`, `UP`,
`W`. `E712` (`== True`/`== False`) e `E501` (linha longa) estão desligadas de
propósito — ver comentários no `pyproject.toml` pra saber o porquê (o
código compara colunas booleanas do SQLAlchemy com `== True` de propósito, e
linhas longas aparecem em HTML inline, textos em português e filtros
SQLAlchemy encadeados — estilo, não bug).

## Testes (pytest + coverage)

```bash
pytest -q                # roda os testes
pytest --cov=app -q      # com relatório de cobertura
```

Os testes ficam em `tests/`. O `tests/conftest.py` configura um banco SQLite
temporário (`DATABASE_URL`) e uma `SECRET_KEY` fixa **antes** de importar
`app.main` — a criação de tabelas e a resolução da chave secreta acontecem no
import do módulo, então a ordem importa. O banco de desenvolvimento
(`licitacoes_saas.db`) nunca é tocado pelos testes.

- `test_auth.py` — registro, login, rejeição de senha errada.
- `test_scoring.py` — testes unitários do motor de pontuação (`app/scoring.py`).
- `test_criterios.py` — CRUD de critérios via API autenticada.

## Arquitetura (import-linter)

```bash
lint-imports
# ou, se o script não estiver no PATH:
python -c "from importlinter.cli import lint_imports_command; lint_imports_command()"
```

Contratos definidos em `pyproject.toml` (`[tool.importlinter]`) — honestos
com a estrutura atual (um monólito flat de rotas em `main.py`, não uma
arquitetura em camadas):

1. `app.database` não pode depender de `app.main`.
2. `app.scoring` e `app.email_utils` são independentes entre si.

## Testes de mutação (mutmut)

```bash
mutmut run       # roda o teste de mutação (usa a config do pyproject.toml)
mutmut results   # mostra o resultado
mutmut show <id> # mostra o diff de um mutante específico
```

**Importante (Windows):** o `mutmut` 3.x se recusa a rodar nativamente no
Windows (pede WSL — [issue #397](https://github.com/boxed/mutmut/issues/397)).
Por isso `requirements-dev.txt` fixa `mutmut==2.4.5`, que roda nativamente e
ainda lê a config de `pyproject.toml` (`[tool.mutmut]`).

Escopo intencionalmente pequeno: só `app/scoring.py` (motor de
filtro/pontuação) e `app/auth.py` (hash de senha, JWT) são mutados —
`main.py` é majoritariamente "cola" de rotas do FastAPI e não vale a pena
mutar ainda.

Se a saída travar com erro de encoding no Windows (emoji não suportado pelo
console cp1252), use:

```bash
python -m mutmut run --simple-output
```

Uma rodada completa pode demorar (mutmut aplica cada mutação, roda a suíte
inteira, e reverte — um mutante por vez). Não precisa rodar até o fim; o
importante é ver mutantes sendo `KILLED` pela suíte de testes.

**Cuidado se interromper uma rodada no meio:** se você matar o processo
enquanto ele está aplicando uma mutação (não entre mutações), o mutmut pode
deixar o arquivo mutado no disco. Ele guarda uma cópia em `app/<arquivo>.bak`
nesse caso — confira `git status`/`git diff` depois de interromper uma
rodada, e restaure do `.bak` se sobrar algum.

## Observabilidade (OpenTelemetry + Sentry)

Ambos são runtime, não dev-only (estão em `requirements.txt`), e ambos são
zero-config por padrão — o app funciona normalmente sem definir nada.

### Tracing (OpenTelemetry)

Sempre ativo: cada requisição gera spans impressos no console
(`ConsoleSpanExporter`) — dá pra ver o tracing local sem configurar nada.

Se você tiver um coletor OTLP rodando (Jaeger local, um coletor Docker, etc.),
defina:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

e os spans também são exportados pra lá (além do console).

### Erros (Sentry)

Desativado por padrão — nenhuma chamada de rede, nenhum SDK inicializado, se
a variável não existir. Pra ativar (depois de criar uma conta gratuita no
Sentry por conta própria):

```bash
export SENTRY_DSN=https://sua-chave@sentry.io/seu-projeto
```

Tudo isso é configurado em `app/observability.py`, chamado uma única vez em
`app/main.py` logo depois de `app = FastAPI(...)`.

## CORS e headers de segurança

`CORS_ORIGINS` controla quais origens podem chamar a API (separadas por
vírgula). Sem a variável, só os origins de desenvolvimento local são aceitos
(`http://localhost:5173`, `http://127.0.0.1:5173`) — nunca `"*"`. Em
produção, defina com o(s) domínio(s) real(is) do frontend:

```bash
export CORS_ORIGINS="https://licittracker-frontend.onrender.com"
```

`app/security_headers.py` adiciona `X-Content-Type-Options`,
`X-Frame-Options` e `Referrer-Policy` em toda resposta. HTTPS/HSTS não são
configurados aqui de propósito — isso é responsabilidade do proxy/hospedagem
quando o app for publicado, não da aplicação.

## SPF, DKIM e DMARC (e-mail)

Isso **não dá pra configurar por código** — são registros DNS do domínio que
envia o e-mail (o `SMTP_FROM`/`SMTP_USER` de `app/email_utils.py`), então
depende de acesso ao provedor de DNS desse domínio.

- **Usando SMTP do Gmail** (o padrão sugerido no README, `SMTP_USER=seuemail@gmail.com`):
  o Gmail já assina e autentica os e-mails enviados pelos servidores dele —
  não precisa configurar nada. A desvantagem é que o remetente aparece como
  "via gmail.com" pra alguns clientes de e-mail, e cai mais fácil em spam em
  volume alto.
- **Usando um domínio próprio** (ex: `notificacoes@licittracker.com.br`):
  aí sim você precisa criar, no provedor de DNS desse domínio:
  - **SPF** — registro TXT autorizando o servidor SMTP a enviar em nome do
    domínio (ex: `v=spf1 include:_spf.google.com ~all` se usar Google
    Workspace, ou o valor específico do seu provedor SMTP).
  - **DKIM** — o provedor SMTP gera um par de chaves; você publica a chave
    pública como registro TXT (geralmente em `<seletor>._domainkey.seudominio.com`).
  - **DMARC** — registro TXT em `_dmarc.seudominio.com` dizendo o que fazer
    com e-mails que falham SPF/DKIM (ex:
    `v=DMARC1; p=quarantine; rua=mailto:voce@seudominio.com`).

Cada provedor (Google Workspace, SES, SendGrid, Mailgun...) te dá os valores
exatos pra copiar — normalmente numa tela de "verificar domínio" no painel
deles.
