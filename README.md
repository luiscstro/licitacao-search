# LicitTracker

Uma plataforma web para monitoramento de licitações públicas de forma personalizada. O sistema permite que usuários criem critérios de busca, acompanhem oportunidades relevantes e visualizem as licitações em um dashboard intuitivo.

O projeto foi desenvolvido como forma de praticar conceitos de desenvolvimento Full Stack, integração com APIs externas e construção de aplicações web utilizando Python e React.

---

## ✨ Funcionalidades

### 👤 Autenticação
- Cadastro de usuários
- Login
- Autenticação baseada em API

### 📋 Gerenciamento de critérios
Cada usuário pode criar seus próprios critérios de monitoramento, definindo:

- Nome do critério
- Palavra-chave obrigatória
- Palavras-chave bônus
- Valor mínimo e máximo
- Estados (UFs)
- Apenas Pregão
- Modo demonstração

Também é possível:

- Editar critérios
- Excluir critérios

---

### 📊 Dashboard de Licitações

O dashboard apresenta as licitações filtradas conforme os critérios cadastrados.

Cada licitação exibe:

- Pontuação de relevância
- Estado (UF)
- Cidade
- Valor estimado
- Número do processo (PNCP)
- Link direto para o edital
- Alerta para licitações próximas do encerramento

Também é possível visualizar:

- Todas as licitações
- Apenas as licitações de um critério específico

---

## 🛠 Tecnologias Utilizadas

### Backend

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Pydantic
- Uvicorn

### Frontend

- React
- Vite
- JavaScript
- CSS

### Integrações

- Portal Nacional de Contratações Públicas (PNCP)

---

# Estrutura do Projeto

```
LicitTracker/

├── backend/
│   ├── app/
│   ├── collector_pncp.py
│   ├── requirements.txt
│   └── licitacoes_saas.db
│
└── frontend/
    ├── src/
    ├── package.json
    └── vite.config.js
```

---

# Como executar

## 1. Clone o projeto

```bash
git clone https://github.com/SEU-USUARIO/LicitTracker.git

cd LicitTracker
```

---

## 2. Backend

Entre na pasta:

```bash
cd backend
```

Crie um ambiente virtual:

### Windows

```bash
python -m venv venv
```

Ative o ambiente:

```bash
venv\Scripts\activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute:

```bash
python -m uvicorn app.main:app --reload
```

O backend ficará disponível em:

```
http://127.0.0.1:8000
```

Documentação:

```
http://127.0.0.1:8000/docs
```

---

## 3. Frontend

Abra outro terminal.

Entre na pasta:

```bash
cd frontend
```

Instale as dependências:

```bash
npm install
```

Execute:

```bash
npm run dev
```

A aplicação ficará disponível em:

```
http://localhost:5173
```

---

## Integração com o PNCP

O projeto utiliza os dados disponibilizados pelo Portal Nacional de Contratações Públicas (PNCP).

Antes de visualizar resultados no dashboard, execute o coletor responsável por popular o banco de dados:

```bash
python collector_pncp.py
```

---

## Notificações por e-mail (resumo diário)

O sistema pode mandar um e-mail diário resumindo as licitações novas que bateram com os critérios de cada empresa. Cada usuário liga/desliga isso em "Notificações" (menu da conta).

Configure as seguintes variáveis de ambiente antes de rodar o envio (no Windows, defina como variável de ambiente do sistema/usuário — Painel de Controle ou `setx`):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seuemail@gmail.com
SMTP_PASSWORD=sua-senha-de-app
SMTP_FROM=seuemail@gmail.com
```

> Se sua conta de e-mail tiver verificação em duas etapas (comum no Gmail/Outlook), use uma **senha de app** — não a senha normal da conta.

Pra rodar manualmente:

```bash
cd backend
python enviar_notificacoes_diarias.py
```

Pra rodar todo dia automaticamente, agende `backend/rodar_notificacoes_diarias.bat` no Agendador de Tarefas do Windows, uns 30 minutos depois do `rodar_coletor_diario.bat` (precisa que a coleta do dia já tenha terminado).

---

## Exportação e indicadores

Na tela de Licitações dá pra exportar o resultado filtrado em CSV, Excel ou PDF. Em "Indicadores" (hub de Ferramentas) dá pra ver gráficos por UF, modalidade e mês de encerramento, sobre o mesmo conjunto filtrado.

---

## Interface

O sistema possui:

- Login e cadastro
- Dashboard de licitações
- Gerenciamento de critérios
- Interface responsiva
- Identidade visual inspirada em documentos oficiais

---

## Objetivos do Projeto

Este projeto foi desenvolvido com os seguintes objetivos:

- Praticar desenvolvimento Full Stack
- Construir APIs REST utilizando FastAPI
- Consumir dados de APIs públicas
- Desenvolver interfaces modernas utilizando React
- Trabalhar autenticação de usuários
- Organizar uma arquitetura cliente-servidor
- Desenvolver um projeto aplicável a um cenário real

---

## Próximos Passos

- Hospedagem do sistema (backend + coletor + notificações rodando na nuvem, não só localmente)
- Notificações por WhatsApp
- Melhorias na experiência do usuário
