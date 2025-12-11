# 🌿 Projeto IRACEMA

### Sistema de Importação e Publicação de Shapefiles no GeoServer  
**Desenvolvido para a Secretaria do Meio Ambiente do Ceará (SEMA/CE)**

---

## 📘 Visão Geral

**Iracema** é um sistema web que automatiza o processo de:

1. Upload de arquivos **Shapefile** (`.zip`);
2. Importação para uma base **PostgreSQL/PostGIS**;
3. Geração automática de tabelas e estilos **SLD**;
4. Publicação das camadas no **GeoServer**, com criação de `featureTypes`, `styles` e `layers` via API REST.

O sistema substitui o fluxo manual via scripts Bash, centralizando tudo em uma interface web moderna (SPA) e uma API Python robusta.

---

## ⚙️ Arquitetura

O sistema segue o padrão **Arquitetura em Cebola (Onion Architecture)**, com as seguintes camadas:

```

iracema/
│
├── Entities/                # Modelos e Helpers de domínio
│   ├── shapefile_entity.py
│   ├── geoserver_helper.py
│   └── ...
│
├── Data/                    # Repositórios e interfaces de persistência
│   ├── interfaces/
│   │   └── i_shapefile_repository.py
│   ├── repositories/
│   │   └── shapefile_repository.py
│   └── db_context.py
│
├── Application/             # DTOs, mapeamentos, serviços e regras de negócio
│   ├── dto/
│   │   └── shapefile_dto.py
│   ├── interfaces/
│   │   └── i_geoserver_service.py
│   ├── services/
│   │   ├── shapefile_service.py
│   │   └── geoserver_service.py
│   └── mappings/
│       └── shapefile_mapper.py
│
├── Presentation/
│   ├── API/                 # Backend (FastAPI)
│   │   ├── controllers/
│   │   │   └── shapefile_controller.py
│   │   ├── main.py
│   │   ├── appsettings.dev.json
│   │   └── appsettings.docker.json
│   │
│   └── UI/                  # Frontend (React)
│       ├── src/
│       │   ├── api/
│       │   │   └── shapefileApi.js
│       │   ├── components/
│       │   │   ├── UploadForm.jsx
│       │   │   ├── TableList.jsx
│       │   │   └── PublishStatus.jsx
│       │   ├── pages/
│       │   │   └── Home.jsx
│       │   └── App.jsx
│       └── package.json
│
└── docker/
├── Dockerfile.api
├── Dockerfile.ui
└── README.md

```

---

## 🧩 Fluxo de Operação

1. O usuário faz upload de um `.zip` contendo `.shp`, `.shx`, `.dbf`, `.prj`;
2. A **API Python** extrai e importa via `ogr2ogr` para o banco **PostGIS**;
3. O serviço **GeoServerService**:
   - Cria o estilo (`POST /styles`);
   - Faz upload do SLD (`PUT /styles/{name}`);
   - Cria o `featureType` (`POST /featuretypes`);
   - Atribui o estilo à camada (`PUT /layers/{workspace}:{layer}`);
4. O **frontend React** exibe logs e status em tempo real.

---

## 🧠 Stack Técnica

| Camada | Tecnologia |
|:-------|:------------|
| Banco de Dados | PostgreSQL 14 + PostGIS 3 |
| Backend | Python 3.11 + FastAPI |
| ORM | SQLAlchemy |
| Frontend | React 18 + Axios + Material UI |
| Comunicação | REST (JSON) |
| Infraestrutura | Docker (sem Compose) |

---

## ⚙️ Configuração

### Arquivos de configuração (`appsettings`)

#### `appsettings.dev.json`

```json
{
  "Database": {
    "Host": "localhost",
    "Port": 5432,
    "User": "postgres",
    "Password": "001q2w3e00",
    "Name": "pedea"
  },
  "GeoServer": {
    "BaseUrl": "http://localhost:8080/geoserver/rest",
    "Workspace": "zcm",
    "Datastore": "zcm_ds",
    "User": "admin",
    "Password": "001q2w3e4r5t6y00"
  },
  "Upload": {
    "TempPath": "/tmp/uploads"
  }
}
```

#### `appsettings.docker.json`

```json
{
  "Database": {
    "Host": "172.18.17.38",
    "Port": 5432,
    "User": "postgres",
    "Password": "001q2w3e00",
    "Name": "pedea"
  },
  "GeoServer": {
    "BaseUrl": "http://172.18.17.38:8080/geoserver/rest",
    "Workspace": "zcm",
    "Datastore": "zcm_ds",
    "User": "admin",
    "Password": "001q2w3e4r5t6y00"
  },
  "Upload": {
    "TempPath": "/app/uploads"
  }
}
```

---

## 🐳 Docker

### Backend (FastAPI)

`docker/Dockerfile.api`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY Presentation/API/ /app/
RUN pip install --no-cache-dir -r requirements.txt
ENV ENVIRONMENT=docker
EXPOSE 9090
CMD ["python", "main.py"]
```

### Frontend (React)

`docker/Dockerfile.ui`

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY Presentation/UI/ /app/
RUN npm install && npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

---

## 🚀 Execução Local

```bash
# Banco
sudo service postgresql start

# API
cd Presentation/API
python main.py

# Frontend
cd Presentation/UI
npm start
```

---

## 🧱 Estrutura das Entidades Principais

### `ShapefileEntity`

```python
class ShapefileEntity:
    def __init__(self, name, path, srid=4674):
        self.name = name
        self.path = path
        self.srid = srid
```

### `ShapefileRepository`

* Importa dados via `ogr2ogr`;
* Gera SQL dinâmico para importação;
* Executa comandos PostgreSQL com `psycopg2`.

### `GeoServerService`

* Envia requisições REST para o GeoServer;
* Gera logs e status por camada;
* Valida publicação e SLD (equivalente aos scripts `::14` e `::15`).

---

## 🧪 Testes Automatizados

* Testes de integração com banco PostGIS;
* Testes de API com `pytest` e `httpx`;
* Mock de GeoServer com `responses`.

---

## 📦 Exemplos de Uso

### Upload e publicação via API

```
POST /api/shapefiles/upload
FormData: { file: shapefile.zip }

→ 200 OK
{
  "layer": "bairro_fortaleza",
  "status": "Publicado com sucesso no GeoServer"
}
```

### Interface Web

* Upload via drag-and-drop;
* Barra de progresso e logs em tempo real;
* Indicadores de status:

  * ✅ Publicado
  * ⚠️ Aguardando estilo
  * ❌ Falha

---

## 🧰 Dependências

### Backend

```
fastapi
uvicorn
psycopg2-binary
sqlalchemy
requests
python-dotenv
```

### Frontend

```
react
axios
material-ui
react-dropzone
```

---

## 🔐 Segurança

* Upload permitido apenas para `.zip` contendo `.shp`, `.dbf`, `.shx`, `.prj`;
* Limite de tamanho configurável;
* API preparada para integração futura com autenticação JWT.