# LicitTracker

Plataforma full stack de monitoramento de licitações públicas brasileiras. O sistema coleta dados do **Portal Nacional de Contratações Públicas (PNCP)**, aplica um motor de pontuação de relevância por empresa e organiza tudo em um fluxo de trabalho completo — da descoberta da oportunidade até o acompanhamento da equipe responsável, passando por favoritos, pipeline de decisão, documentos e indicadores.

Projeto pessoal desenvolvido para aprofundar conhecimentos de desenvolvimento Full Stack: back-end com Python/FastAPI, front-end com React, integração com API pública, arquitetura multiempresa e práticas de engenharia de software (testes automatizados, observabilidade, qualidade de código e workflow de Git baseado em Issue → Branch → PR).

---

## Funcionalidades

### Autenticação e segurança
- Login com JWT: access token de vida curta (60 min) e refresh token revogável, com rotação a cada uso
- Rate limiting no login contra força bruta
- CORS restrito por lista de origens permitidas e headers de segurança de resposta (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)

### Equipe
- Empresas com múltiplos usuários (multiempresa/multiusuário)
- Sincronização de dados da empresa por CNPJ (com validação de dígito verificador, cache e rate limiting nas APIs externas)
- Convite de membros para a equipe

### Critérios de monitoramento
Cada empresa pode criar seus próprios critérios de busca, definindo:

- Nome do critério
- Palavra-chave obrigatória e palavras-chave bônus
- Valor mínimo e máximo
- Estados (UFs)
- Apenas Pregão
- Modo demonstração

Critérios podem ser editados e excluídos a qualquer momento.

### Dashboard de Licitações
- Licitações filtradas e pontuadas conforme os critérios cadastrados (motor de *scoring* de relevância)
- Estado (UF), cidade, valor estimado, número do processo (PNCP) e link direto para o edital
- Alerta para licitações próximas do encerramento
- Visualização de todas as licitações ou apenas as de um critério específico
- Exportação dos resultados filtrados em CSV, Excel ou PDF

### Favoritos e Pipeline
- Marcação de licitações como favoritas para acompanhamento rápido
- Pipeline (kanban) de oportunidades, compartilhado pela equipe, com etapas de decisão por licitação
- Comentários por licitação, para registrar o histórico de análise da equipe

### Documentos
- Upload, substituição e histórico de versões de documentos por licitação/empresa
- Indicadores de completude documental

### Indicadores
- Gráficos por UF, modalidade e mês de encerramento sobre o conjunto filtrado (hub de Ferramentas)

### Notificações
- Resumo diário por e-mail das licitações novas que bateram com os critérios de cada empresa
- Ativação/desativação por usuário

---

## Tecnologias Utilizadas

### Backend
- Python + FastAPI
- SQLAlchemy + PostgreSQL (produção) / SQLite (desenvolvimento local)
- Pydantic
- `openpyxl` / `fpdf2` para exportação (Excel/PDF)
- Uvicorn

### Frontend
- React + Vite
- Recharts (gráficos)
- Lucide React (ícones)

### Qualidade e observabilidade
- **Testes**: Pytest (backend) · Vitest + Testing Library (unitário/componentes) · Playwright (E2E) · Stryker (mutation testing)
- **Lint/formatação**: Ruff (backend) · Biome (frontend)
- **Arquitetura**: import-linter (backend) · dependency-cruiser + Knip (frontend, dependências não usadas/circulares)
- **Observabilidade**: OpenTelemetry (tracing) e Sentry (erros), ambos opcionais e zero-config por padrão
- **Git**: Commitlint + Husky (Conventional Commits), workflow Issue → Branch → PR

### Integrações
- Portal Nacional de Contratações Públicas (PNCP)

---

## Estrutura do Projeto

```
LicitTracker/
├── backend/
│   ├── app/                          # FastAPI: rotas, models, schemas, auth, scoring, e-mail, observabilidade
│   ├── tests/                        # Pytest
│   ├── migrations/                   # Scripts de migração de dados
│   ├── collector_pncp.py             # Coletor de licitações do PNCP
│   ├── enviar_notificacoes_diarias.py
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── pages/                    # Dashboard, Critérios, Favoritos, Pipeline, Equipe, Documentos, Indicadores...
    │   └── components/
    ├── e2e/                          # Playwright
    └── package.json
```

---

## Como executar

### 1. Clone o projeto

```bash
git clone https://github.com/SEU-USUARIO/LicitTracker.git
cd LicitTracker
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Documentação interativa (Swagger): `http://127.0.0.1:8000/docs`

### 3. Frontend

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Aplicação disponível em `http://localhost:5173`

### 4. Coleta de dados do PNCP

Antes de visualizar resultados no dashboard, execute o coletor responsável por popular o banco de dados:

```bash
cd backend
python collector_pncp.py
```

---

## Deploy

Passo a passo pra publicar o backend (Discloud) e o frontend (Render) em
[`DEPLOY.md`](DEPLOY.md).

---

## Notificações por e-mail (resumo diário)

O sistema pode enviar um e-mail diário resumindo as licitações novas que bateram com os critérios de cada empresa. Cada usuário liga/desliga isso em "Notificações" (menu da conta).

Configure as seguintes variáveis de ambiente antes de rodar o envio (no Windows, via Painel de Controle ou `setx`):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seuemail@gmail.com
SMTP_PASSWORD=sua-senha-de-app
SMTP_FROM=seuemail@gmail.com
```

> Se sua conta de e-mail tiver verificação em duas etapas (comum no Gmail/Outlook), use uma **senha de app** — não a senha normal da conta.

Para rodar manualmente:

```bash
cd backend
python enviar_notificacoes_diarias.py
```

Para rodar todo dia automaticamente, agende `backend/rodar_notificacoes_diarias.bat` no Agendador de Tarefas do Windows, uns 30 minutos depois do `rodar_coletor_diario.bat` (precisa que a coleta do dia já tenha terminado).

---

## Qualidade de código e testes

Detalhes completos em [`backend/DEVELOPMENT.md`](backend/DEVELOPMENT.md).

```bash
# Backend
cd backend
pytest -q                      # testes
pytest --cov=app -q            # com cobertura
ruff check .                   # lint
lint-imports                   # contratos de arquitetura

# Frontend
cd frontend
npm run test                   # testes unitários (Vitest)
npm run test:e2e               # end-to-end (Playwright)
npm run lint                   # lint (Biome)
npm run knip                   # dependências/exports não usados
npm run depcruise               # dependências circulares/indevidas
```

---

## Workflow de contribuição

Este repositório segue o fluxo **Issue → Branch → PR** para qualquer correção,
melhoria ou nova funcionalidade: uma Issue descreve o problema, uma branch
(`fix/…`, `feat/…`, `chore/…`) implementa a mudança, e um Pull Request liga as
duas antes de qualquer merge em `main`. Detalhes em [`CLAUDE.md`](CLAUDE.md).

---

## Objetivos do Projeto

Este projeto foi desenvolvido com os seguintes objetivos:

- Praticar desenvolvimento Full Stack de ponta a ponta (API + interface)
- Construir APIs REST com FastAPI, com arquitetura multiempresa
- Consumir e tratar dados de uma API pública real (PNCP)
- Desenvolver interfaces modernas e responsivas com React
- Aplicar boas práticas de engenharia: testes automatizados (unitários, integração, E2E e mutação), observabilidade e análise estática de arquitetura
- Organizar um workflow de Git rastreável (Issue → Branch → PR)
- Entregar um projeto aplicável a um cenário real de mercado

---

## Interface

O sistema possui:

- Dashboard de licitações
- Gerenciamento de critérios
- Pipeline de oportunidades, favoritos e comentários
- Gestão de equipe e documentos
- Interface responsiva com identidade visual inspirada em documentos oficiais

---

## Próximos Passos

- Notificações por WhatsApp
- Melhorias na experiência do usuário
