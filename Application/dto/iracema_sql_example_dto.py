# Application/dto/iracema_sql_example_dto.py
from dataclasses import dataclass

@dataclass
class IracemaSqlExampleDto:
    question: str
    sql: str
