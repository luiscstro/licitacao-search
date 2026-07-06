# 🎯 PNCP LicitTracker

Um rastreador automatizado construído em Python para monitorar, filtrar e ranquear propostas de licitações públicas utilizando a API oficial do Portal Nacional de Contratações Públicas (PNCP). 

O sistema avalia oportunidades diárias com base em regras de negócio pré-definidas, armazena o histórico em um banco de dados local e gera um dashboard estático em HTML para análise rápida e tomada de decisão.

## ✨ Funcionalidades

* **Integração Oficial:** Consome a API pública do PNCP diretamente, sem necessidade de autenticação, *cookies* ou *web scraping* de HTML.
* **Resiliência e Estabilidade:** Implementa um sistema robusto de *retries* com *exponential backoff* para lidar nativamente com instabilidades do servidor governamental e bloqueios por *Rate Limit* (HTTP 429).
* **Persistência Inteligente:** Utiliza SQLite (`db.py`) para manter o histórico de buscas. O banco deduplica registros, identifica propostas recém-lançadas (destacadas com a tag `NOVA`) e inativa automaticamente certames cujo prazo encerrou ou que saíram do radar da API.
* **Filtros de Negócio e Ranqueamento:** Avalia cada contrato com base em um sistema de pontuação (*score*) que prioriza:
  * Palavras-chave específicas (ex: limpeza, apoio administrativo).
  * Limites de valor estimado.
  * Região de execução (prioridade configurada para o Maranhão e estados vizinhos).
  * Exigência de Dedicação Exclusiva de Mão de Obra (DEMO).
* **Dashboard Automático:** Gera localmente um arquivo `licitacoes.html` responsivo, organizado do maior para o menor *score*, com links diretos para os editais oficiais.

## 📁 Estrutura do Projeto

* `buscar_licitacoes.py`: Script principal. Gerencia as requisições à API, aplica as lógicas de filtro de negócio, calcula o *score* e monta a interface HTML.
* `db.py`: Módulo de banco de dados. Responsável pelas operações CRUD no SQLite e pela regra de negócio que define se uma licitação é nova ou inativa.
* `licitacoes.db`: Arquivo do banco de dados SQLite (gerado automaticamente na primeira execução).
* `licitacoes.html`: Dashboard gerado ao final de cada execução do script.

## 🚀 Como Usar

### 1. Pré-requisitos
Certifique-se de ter o [Python 3.8+](https://www.python.org/) instalado em sua máquina. O único pacote externo necessário é o `requests`.

### 2. Instalação
Clone o repositório e crie um ambiente virtual:

```bash
# Crie o ambiente virtual
python -m venv venv

# Ative o ambiente virtual (Windows)
.\venv\Scripts\activate

# Ative o ambiente virtual (Linux/macOS)
source venv/bin/activate

# Instale as dependências
pip install requests
