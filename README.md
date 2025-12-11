Aqui está um **README.md profissional, completo e pronto para usar** no repositório do projeto **Iracema** — seguindo Clean Architecture, com explicações de stack, fluxo, instalação, execução, uso e arquitetura interna.

Ele foi escrito considerando **todo o código que já desenvolvemos**, incluindo:

* FastAPI
* ChromaDB
* LangChain
* Phi-3 / Ollama
* OpenAI API-like providers
* Clean Architecture
* Serviços Ask / LLM Client
* Controllers
* Dockerfile

Caso queira que ele fique **mais resumido**, **mais técnico**, ou **com diagramas**, posso ajustar.

---

# 📘 **Iracema — Sistema de Consultas Inteligentes sobre Zoneamento Costeiro (ZEEC/CE)**

Iracema é um **chatbot geoespacial inteligente** que responde perguntas em linguagem natural sobre os dados de zoneamento costeiro do Ceará (ZEEC), utilizando:

* **Geração de SQL por LLM**
* **Execução real sobre PostgreSQL/PostGIS**
* **Explicação semântica dos resultados**
* **Orquestração segura e auditável**
* **Arquitetura limpa (Clean Architecture)**

O objetivo do MVP é responder perguntas exclusivamente sobre a tabela:

```
1201_ce_zeec_zoneamento_p_litora_2021_pol
```

---

# 🧠 **Stack Principal**

### 🔹 **Backend**

* **FastAPI**
* **Python 3.11**
* **SQLAlchemy**
* **PostgreSQL/PostGIS**
* **Pydantic v2**
* **PyJWT (autenticação)**

### 🔹 **LLM / IA**

* **Phi-3 (Ollama)** *ou* qualquer modelo compatível com **OpenAI API**
* **LangChain**
* **ChromaDB (RAG opcional)**

### 🔹 **Arquitetura**

* Clean Architecture com 5 camadas:

  * **Models**
  * **Data**
  * **Application**
  * **External**
  * **Presentation (API)**

---

# 📁 **Estrutura do Projeto**

```
Iracema/
│
├── Models/               # Entidades internas (conversas, mensagens, logs)
│   ├── iracema_conversation.py
│   ├── iracema_message.py
│   ├── iracema_sql_log.py
│   └── iracema_enums.py
│
├── Data/
│   ├── db_context.py
│   └── repositories/
│
├── Application/
│   ├── dto/
│   ├── interfaces/
│   ├── helpers/
│   └── services/
│
├── External/
│   ├── ai/
│   │   ├── llm_provider_base.py
│   │   ├── openai_llm_provider.py
│   │   ├── phi3_local_llm_provider.py
│   │   └── langchain_phi3_provider.py
│   └── vector/
│       ├── vector_store_base.py
│       └── chromadb_vector_store.py
│
└── Presentation/
    ├── API/
    │   ├── controllers/
    │   ├── helpers/
    │   ├── settings.py
    │   ├── main.py
    │   └── requirements.txt
    └── Dockerfile
```

---

# 🔄 **Fluxo de Funcionamento**

## 1. Usuário faz pergunta ao endpoint:

```
POST /iracema-api/v1/ask
```

## 2. A Iracema executa o pipeline:

```
Pergunta → Geração de SQL → Execução no PostgreSQL 
→ Explicação → Resposta Final
```

### ✔ **Primeira chamada ao LLM (Phi-3 / OpenAI / Ollama)**

* Gera SQL seguro e validado.

### ✔ **Execução real no banco**

* O SQL roda em PostgreSQL/PostGIS.
* Apenas SELECT permitido.

### ✔ **Segunda chamada ao LLM**

* Explica o resultado da consulta.
* Gera texto natural contextualizado.

---

# 🗄 **Banco de Dados Utilizado**

No MVP só usamos a tabela:

```sql
CREATE TABLE IF NOT EXISTS public."1201_ce_zeec_zoneamento_p_litora_2021_pol"
(
    gid integer PRIMARY KEY,
    id numeric,
    zonas varchar(254),
    sub_zonas varchar(254),
    letra_subz varchar(254),
    perimet_km numeric,
    area_km2 numeric,
    geom geometry(MultiPolygon,4674)
);
```

> A geometria não é usada no MVP, apenas atributos tabulares.

---

# 🚀 **Como Rodar Localmente**

## 1. Instalar dependências do Ubuntu

```bash
sudo apt update

sudo apt install -y \
  python3-dev python3-pip build-essential gcc g++ \
  libssl-dev libffi-dev cmake git \
  libblas-dev liblapack-dev libstdc++6
```

## 2. Instalar Ollama (opcional mas recomendado)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3
ollama serve
```

## 3. Criar ambiente Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r Presentation/API/requirements.txt
```

## 4. Configurar `appsettings.dev.json`

Exemplo:

```json
{
  "Database": {
    "Host": "localhost",
    "Port": 5432,
    "User": "postgres",
    "Password": "123",
    "Name": "iracema_db"
  },
  "LLM": {
    "ApiKey": "dummy",
    "BaseUrl": "http://localhost:11434/v1",
    "ModelSql": "phi3",
    "ModelExplainer": "phi3"
  }
}
```

## 5. Iniciar a API

```bash
uvicorn Presentation.API.main:app --host 0.0.0.0 --port 9090 --reload
```

---

# 🐋 **Rodar via Docker**

Build:

```bash
docker build -t iracema-api .
```

Run:

```bash
docker run -d \
  -p 9090:9090 \
  -e ENVIRONMENT=docker \
  iracema-api
```

---

# 💬 **Exemplo de Requisição**

```bash
curl -X POST http://localhost:9090/iracema-api/v1/ask \
  -H "Authorization: Bearer <seu_token>" \
  -H "Content-Type: application/json" \
  -d '{
        "conversationId": null,
        "question": "Quais são as zonas com maior area_km2?"
      }'
```

---

# 📜 **Segurança**

Iracema usa:

* JWT baseado em PyJWT
* Logs completos de:

  * perguntas
  * SQL gerados
  * respostas
* Regras de segurança:

  * Somente `SELECT` permitido
  * SQL validado previamente
  * Conversas e mensagens persistidas

---

# 🧪 **Testes de SQL Automaticamente Gerados**

Exemplos de perguntas suportadas:

* *"Quais zonas têm maior área acumulada?"*
* *"Liste as subzonas e ordene por perímetro."*
* *"Quais zonas possuem letra_subz igual a 'A'?"*

O LLM sempre gera SQL válidos como:

```sql
SELECT zonas, area_km2
FROM "1201_ce_zeec_zoneamento_p_litora_2021_pol"
ORDER BY area_km2 DESC
LIMIT 10;
```

---

# 🖥 **Roadmap**

| Fase | Funcionalidade                          |
| ---- | --------------------------------------- |
| MVP  | Perguntas tabulares (SELECTs)           |
| 1.1  | RAG usando ChromaDB                     |
| 1.2  | Suporte a todas as tabelas da PEDEA     |

Perfeito — vou adicionar ao **README.md** uma seção profissional explicando:

* Trunk Based Development (TBD)
* Padrão de commits semânticos (conventional commits)
* Como usar as tags (`feat`, `fix`, `chore`, `refactor`, `docs`, etc.)
* Como isso se encaixa no fluxo do projeto Iracema

Vou inserir no final do README, logo antes da seção **Contribuição**.

---

# 🪵 **Trunk Based Development (TBD)**

O projeto **Iracema** adota o modelo **Trunk Based Development**, que é hoje o padrão para equipes de alta performance, CI/CD rápido e entregas contínuas.

### ✔ Princípios aplicados no Iracema

1. **A branch principal é sempre deployável**
   Toda mudança integrada no `main` deve estar estável.

2. **Commits pequenos, frequentes e integrados rapidamente**
   Branches curtas, típicas de 30 minutos a poucas horas.

3. **Sem branches long-lived**
   Nada de branches que ficam dias ou semanas desviadas da `main`.

4. **Feature flags** para funcionalidades incompletas
   Raramente usamos branches longas; usamos toggles quando necessário.

5. **CI automático** executado a cada push
   Garante que falhas sejam detectadas imediatamente.

6. **Pull Requests curtos** e rápidos de revisar
   PRs longos são evitados.

### ✔ Benefícios para o projeto Iracema

* Evita divergência entre camadas (Application, Data, External…).
* Permite evoluir a arquitetura (LLM providers, Chroma, RAG) sem grandes rupturas.
* Facilita refatorações e reorganização de pastas.
* Garante que a API esteja sempre em um estado executável.

---

# 📝 **Commits Semânticos (Conventional Commits)**

Todos os commits devem seguir o padrão:

```
<tipo>(escopo opcional): descrição curta
```

### 🔹 Tipos aceitos no projeto

| Tipo         | Quando usar                                               |
| ------------ | --------------------------------------------------------- |
| **feat**     | Nova funcionalidade (ex.: novo controller, novo provider) |
| **fix**      | Correção de bug (ex.: SQL inválido, erro no provider)     |
| **chore**    | Tarefas de manutenção (configs, scripts, renomeações)     |
| **docs**     | Alterações no README, documentação, comentários           |
| **refactor** | Refatoração sem mudar comportamento da API                |
| **test**     | Inclusão ou ajuste de testes                              |
| **perf**     | Melhorias de performance (ex.: cache, otimização SQL)     |
| **build**    | Mudanças em Dockerfile, pipeline, dependências            |
| **ci**       | Ajustes em CI/CD                                          |
| **style**    | Alterações que não modificam lógica (lint, formatação)    |

### ✔ Exemplos reais para o projeto Iracema

#### 1. Nova feature

```
feat(api): adicionar endpoint /ask para consultas naturais
```

#### 2. Correção de bug

```
fix(sql): corrigir validação de SELECT no gerador de SQL
```

#### 3. Alteração estrutural

```
refactor(architecture): mover camada Entities para Models
```

#### 4. Documentação

```
docs: adicionar seção de trunk based development ao README
```

#### 5. Ajuste do Ollama Provider

```
feat(external): implementar Phi3LocalLLMProvider baseado em Ollama
```

#### 6. Configuração

```
chore(settings): adicionar configs de LLM no appsettings.dev.json
```

---

# 🧭 **Como fica o fluxo de desenvolvimento**

### 1️⃣ Criar uma branch curta a partir da main:

```
git checkout -b feat/ask-service
```

### 2️⃣ Fazer commits semânticos:

```
git commit -m "feat(ask): implementar serviço principal de orquestração"
```

### 3️⃣ Push rápido e PR curto:

```
git push -u origin feat/ask-service
```

### 4️⃣ Revisão e merge imediato na main

(sem long-lived branches)

### 5️⃣ Deploy automatizado ou manual

---

# 🏷 **Tags de versão (opcional)**

Usamos semver:

```
v1.0.0
v1.1.0
v1.1.1
```

Tags são criadas apenas em commits estáveis da `main`.

---

# 🧩 Integração com o Pipeline de LLM

O padrão de commits e TBD é extremamente útil no Iracema porque:

* Nova camada External não quebra Application
* Mudança no provider não afeta controllers
* Novos prompts podem ser adicionados sem refatorações gigantes
* RAG pode ser plugado e desplugado dinamicamente