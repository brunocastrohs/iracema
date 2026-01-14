# Data/Entities/iracema_enums.py

from enum import Enum


class LLMProviderEnum(str, Enum):
    OPENAI = "OPENAI"
    AZURE_OPENAI = "AZURE_OPENAI"
    OLLAMA = "OLLAMA"
    LOCAL = "LOCAL"


class LLMModelEnum(str, Enum):
    PHI_3 = "PHI-3"
    LLAMA_3 = "LLAMA-3"
    GPT_4O = "GPT-4O"
    OTHER = "OTHER"


class MessageRoleEnum(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class QueryStatusEnum(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"

class ConversationPhaseEnum(str, Enum):
    START = "START"   # resolvendo contexto (datasource/tabela)
    ASK = "ASK"       # perguntas já com contexto fixado


class ConversationContextStatusEnum(str, Enum):
    EMPTY = "EMPTY"                 # sem datasource
    SELECTING = "SELECTING"         # start em andamento (interações múltiplas)
    READY = "READY"                 # datasource fixado, pronto para /ask
    BLOCKED = "BLOCKED"             # sem permissão / inativo / erro de governança