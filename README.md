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

- Hospedagem do sistema
- Autenticação utilizando JWT
- Notificações por e-mail
- Atualização automática das licitações
- Dashboard com gráficos e indicadores
- Favoritar licitações
- Exportação de resultados
- Melhorias na experiência do usuário
