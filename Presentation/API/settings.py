import json
import os
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


class _Settings(BaseModel):
    # DB
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # API
    API_TITLE: str = Field(default="Iracema API")
    API_VERSION: str = Field(default="1.0.0")
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=9090)
    API_PREFIX: str = Field(default="/iracema-api/v1")
    API_RELOAD_ON_DEV: bool = Field(default=True)

    # CORS
    CORS_ALLOW_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"])

    # JWT
    JWT_SECRET: str = Field(default="iracema_dev_secret_change_me")
    JWT_ISSUER: str = Field(default="Iracema")
    JWT_AUDIENCE: str = Field(default="IracemaClient")
    JWT_EXPIRES_MINUTES: int = Field(default=120)

    # LLM (Iracema)
    LLM_PROVIDER: str = Field(default="ollama")
    LLM_BASE_URL: str = Field(default="http://localhost:11434")
    LLM_MODEL_SQL: str = Field(default="phi3")
    LLM_MODEL_EXPLAINER: str = Field(default="phi3")
    LLM_TEMPERATURE: float = Field(default=0.0)
    
    VECTORSTORE_DIR: str = Field(default="/var/lib/iracema/chroma")

    TOP_K: int = Field(default=10)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_config_file() -> Path:
    env = os.getenv("ENVIRONMENT", "dev").lower()
    base = Path(__file__).parent
    return base / ("appsettings.docker.json" if env == "docker" else "appsettings.dev.json")


_cfg = _load_json(_resolve_config_file())


_MISSING = object()

def _get(path: str, default=None):
    cur = _cfg
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    # aqui cur pode ser False/0/"" e ainda é válido
    return cur if cur is not _MISSING else default


settings = _Settings(
    # DB
    DB_HOST=_get("Database.Host"),
    DB_PORT=int(_get("Database.Port")),
    DB_USER=_get("Database.User"),
    DB_PASSWORD=_get("Database.Password"),
    DB_NAME=_get("Database.Name"),
    
    TOP_K=_get("TOP_K"),

    # API
    API_TITLE=_get("Api.Title", "Iracema API"),
    API_VERSION=_get("Api.Version", "1.0.0"),
    API_HOST=_get("Api.Host", "0.0.0.0"),
    API_PORT=int(_get("Api.Port", 9090)),
    API_PREFIX=_get("Api.Prefix", "/iracema-api/v1"),
    API_RELOAD_ON_DEV=bool(_get("Api.ReloadOnDev", True)),

    # CORS
    CORS_ALLOW_ORIGINS=_get("Cors.AllowOrigins", ["*"]),
    CORS_ALLOW_CREDENTIALS=bool(_get("Cors.AllowCredentials", True)),
    CORS_ALLOW_METHODS=_get("Cors.AllowMethods", ["*"]),
    CORS_ALLOW_HEADERS=_get("Cors.AllowHeaders", ["*"]),

    # JWT
    JWT_SECRET=_get("Jwt.Secret", "iracema_dev_secret_change_me"),
    JWT_ISSUER=_get("Jwt.Issuer", "Iracema"),
    JWT_AUDIENCE=_get("Jwt.Audience", "IracemaClient"),
    JWT_EXPIRES_MINUTES=int(_get("Jwt.ExpiresMinutes", 120)),

    # LLM
    LLM_PROVIDER=_get("LLM.Provider", "ollama"),
    LLM_BASE_URL=_get("LLM.BaseUrl", "http://localhost:11434"),
    LLM_MODEL_SQL=_get("LLM.ModelSql", "phi3"),
    LLM_MODEL_EXPLAINER=_get("LLM.ModelExplainer", "phi3"),
    LLM_TEMPERATURE=float(_get("LLM.Temperature", 0.0)),
    
    VECTORSTORE_DIR=_get("VectorStore.Dir", "/var/lib/iracema/chroma"),

)