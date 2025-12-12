from typing import Any, Dict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from Presentation.API.settings import settings

from Data.db_context import DbContext
from Data.repositories.iracema_conversation_repository import IracemaConversationRepository
from Data.repositories.iracema_message_repository import IracemaMessageRepository
from Data.repositories.iracema_sql_log_repository import IracemaSQLLogRepository

from Models.iracema_enums import LLMProviderEnum, LLMModelEnum

from Application.interfaces.i_iracema_ask_service import IIracemaAskService
from Application.services.iracema_ask_service import IracemaAskService
from Application.services.iracema_llm_client_service import IracemaLLMClient

from External.vector.chromadb_vector_store import ChromaDBVectorStore


# -----------------------------------------------------------------------------
# Auth (JWT Bearer)
# -----------------------------------------------------------------------------

_security = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> Dict[str, Any]:
    """
    Valida o token JWT emitido pelo /auth/login.
    Retorna o payload (sub, roles, etc.) se o token for válido.
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        )

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )


# -----------------------------------------------------------------------------
# Wiring do IracemaAskService
# -----------------------------------------------------------------------------

# DbContext singleton (process-wide)
_db_context = DbContext(
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    db=settings.DB_NAME,
)

# Repositórios (stateless; usam session passada nos métodos)
_conversation_repo = IracemaConversationRepository(_db_context)
_message_repo = IracemaMessageRepository(_db_context)
_sql_log_repo = IracemaSQLLogRepository(_db_context)

# Vector store (Chroma persistente)
# DICA DEV: use algo como ~/.iracema/chroma para evitar permissão em /var/lib
_vector_store = ChromaDBVectorStore(
    persist_directory=getattr(settings, "VECTORSTORE_DIR", "/var/lib/iracema/chroma")
)

# Cliente LLM (orquestra provider + prompts)
_llm_client = IracemaLLMClient(
    vector_store=_vector_store,
    settings=settings,
)

# Service principal
_ask_service: IIracemaAskService = IracemaAskService(
    db_context=_db_context,
    conversation_repo=_conversation_repo,
    message_repo=_message_repo,
    sql_log_repo=_sql_log_repo,
    llm_client=_llm_client,
    llm_provider=LLMProviderEnum.OLLAMA,  # para log/auditoria
    llm_model=LLMModelEnum.PHI_3,         # para log/auditoria
)


def get_iracema_ask_service() -> IIracemaAskService:
    return _ask_service
