# Presentation/API/controllers/helpers/iracema_dependencies_helper.py

from typing import Any, Dict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from Presentation.API.settings import settings
from Presentation.API.controllers.auth_controller import (
    JWT_SECRET,
    JWT_ISSUER,
    JWT_AUDIENCE,
    JWT_ALG,
)

from Data.db_context import DbContext
from Data.repositories.iracema_conversation_repository import IracemaConversationRepository
from Data.repositories.iracema_message_repository import IracemaMessageRepository
from Data.repositories.iracema_sql_log_repository import IracemaSQLLogRepository
from Models.iracema_enums import LLMProviderEnum, LLMModelEnum

from Application.interfaces.i_iracema_ask_service import IIracemaAskService
from Application.services.iracema_ask_service import IracemaAskService
from Application.services.iracema_llm_client_service import IracemaLLMClient

from External.ai.openai_llm_provider import OpenAILLMProvider
from External.ai.langchain_phi3_provider import LangChainPhi3Provider
from External.vector.chromadb_vector_store import ChromaDBVectorStore
# Se quiser usar LangChain + Phi-3 + Chroma depois:
# from External.ai.langchain_phi3_provider import LangChainPhi3Provider
# from External.vector.chromadb_vector_store import ChromaDBVectorStore


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
            JWT_SECRET,
            algorithms=[JWT_ALG],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
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

# DbContext único do projeto
_db_context = DbContext(
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    db=settings.DB_NAME,
)

# Repositórios do domínio Iracema
_conversation_repo = IracemaConversationRepository(_db_context)
_message_repo = IracemaMessageRepository(_db_context)
_sql_log_repo = IracemaSQLLogRepository(_db_context)

# -----------------------------------------------------------------------------
# Provider de LLM (camada External)
# -----------------------------------------------------------------------------

# Modo atual: API compatível com OpenAI (pode ser GPT, Phi-3, Llama-3, etc.)
#_llm_provider = OpenAILLMProvider(
#    api_key=settings.LLM_API_KEY,
#    base_url=settings.LLM_BASE_URL,
#)
vector_store = ChromaDBVectorStore(persist_directory="/var/lib/iracema/chroma")
retriever = vector_store.as_retriever()

_llm_provider = LangChainPhi3Provider(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    model=settings.LLM_MODEL_SQL,
    retriever=retriever,
)

# 👉 Se quiser trocar para LangChain + Phi-3 + Chroma, basta:
# vector_store = ChromaDBVectorStore(persist_directory="/caminho/do/chroma")
# retriever = vector_store.as_retriever()
# _llm_provider = LangChainPhi3Provider(
#     api_key=settings.LLM_API_KEY,
#     base_url=settings.LLM_BASE_URL,
#     model=settings.LLM_MODEL_SQL,
#     retriever=retriever,
# )

_llm_client = IracemaLLMClient(
    provider=_llm_provider,
    model_sql=settings.LLM_MODEL_SQL,
    model_explainer=settings.LLM_MODEL_EXPLAINER or settings.LLM_MODEL_SQL,
)

_ask_service: IIracemaAskService = IracemaAskService(
    db_context=_db_context,
    conversation_repo=_conversation_repo,
    message_repo=_message_repo,
    sql_log_repo=_sql_log_repo,
    llm_client=_llm_client,
    llm_provider=LLMProviderEnum.OPENAI,  # apenas para fins de log/auditoria
    llm_model=LLMModelEnum.PHI_3,         # idem
)


def get_iracema_ask_service() -> IIracemaAskService:
    """
    Dependência a ser usada na controller para obter o service principal.
    """
    return _ask_service
