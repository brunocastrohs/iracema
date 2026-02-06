# 🧠 Iracema (Backend)

**Iracema** é um **assistente inteligente orientado a dados**, projetado para interpretar perguntas em linguagem natural, convertê-las em consultas estruturadas sobre **PostgreSQL/PostGIS**, executar essas consultas de forma segura e fornecer explicações opcionais sobre os resultados.

> ⚠️ **Iracema NÃO é um chatbot genérico.**  
> Ela não responde sem consultar dados reais, não “conversa por conversar” e não inventa respostas.  
> O foco é **consulta estruturada, segurança, auditoria e rastreabilidade**.

---

## 🎯 Objetivo

- Consultar bases PostgreSQL/PostGIS usando linguagem natural  
- Garantir rastreabilidade completa:  
  **Pergunta → Plano → SQL → Resultado → Explicação**
- Suportar múltiplos modos de geração de consultas:
  - Heurístico (templates)
  - AI (LLM gera SQL)
  - Function Calling (LLM gera plano JSON → SQL determinístico)

---

## 🧭 Arquitetura em Camadas

- **Presentation** – API FastAPI
- **Application** – Serviços, DTOs, helpers e regras de negócio
- **Domain** – Modelos e contratos
- **Data** – Repositórios e contexto de banco
- **External** – Integração com LLM (Ollama) e RAG
- **External/vector** – ChromaDB para cache semântico

---

## 📁 Estrutura de Pastas

```bash
.
├── Application
│   ├── dto
│   ├── helpers
│   ├── interfaces
│   ├── mappings
│   └── services
│
├── Data
│   ├── repositories
│   └── db_context.py
│
├── Domain
│   ├── interfaces
│   ├── datasource_model.py
│   ├── iracema_conversation_context_model.py
│   ├── iracema_conversation_model.py
│   ├── iracema_enums.py
│   ├── iracema_message_model.py
│   └── iracema_sql_log_model.py
│
├── External
│   ├── ai
│   │   ├── iracema_fc_client_ollama.py
│   │   └── langchain_ollama_provider.py
│   └── vector
│       ├── chromadb_vector_store.py
│       └── vector_store_base.py
│
└── Presentation
    └── API
        ├── controllers
        │   ├── ask_controller.py
        │   ├── auth_controller.py
        │   └── start_controller.py
        ├── helpers
        ├── workers
        │   └── scheduler.py
        ├── appsettings.dev.json
        ├── appsettings.docker.json
        ├── main.py
        ├── requirements.txt
        └── settings.py
```

---

## 🚀 Execução Local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r Presentation/API/requirements.txt
```

```bash
export ENVIRONMENT=dev
export PYTHONPATH=$PWD
```

```bash
uvicorn Presentation.API.main:app --host 0.0.0.0 --port 9090 --reload
```

---

## 🔐 Autenticação

- JWT Bearer
- Endpoint: `POST /{API_PREFIX}/auth/login`
- Todas as rotas `/chat/*` exigem token válido

> ⚠️ Segredos **não devem** ser expostos em repositório ou README.

---

## 📬 Endpoints Principais

- `POST /chat/ask` – pipeline padrão
- `POST /chat/ask/heuristic` – apenas heurística
- `POST /chat/ask/ai` – LLM gera SQL
- `POST /chat/ask/fc` – **Function Calling (recomendado)**

---

## 🧠 Function Calling (FC)

No modo FC:
- O LLM **não gera SQL**
- Ele retorna um **plano JSON estruturado**
- O backend:
  - valida colunas
  - aplica regras de segurança
  - compila SQL determinístico
  - executa e audita

Isso garante:
- Segurança
- Reprodutibilidade
- Explicabilidade

---

## 📊 Auditoria

Toda execução gera:
- Conversa
- Mensagens
- SQL Log (tempo, rows, status, modelo, motivo)

---

## 🗂️ RAG (ChromaDB)

Consultas bem-sucedidas são indexadas para:
- Reuso de SQL validado
- Redução de chamadas ao LLM
- Aumento de precisão ao longo do tempo

---

## 🛡️ Segurança

- Apenas SELECT
- Sem DDL/DML
- Whitelist de colunas
- Geometrias bloqueadas
- LIMIT sempre aplicado

---

## 🧭 Roadmap

- [x] FastAPI + Lifespan
- [x] Function Calling determinístico
- [x] Auditoria completa
- [x] RAG
- [ ] JOINs controlados
- [ ] Explain em JSON
- [ ] Métrica de confiança