# Application/helpers/sql/sql_types.py

from dataclasses import dataclass

@dataclass
class SqlPlan:
    sql: str
    used_template: bool
    reason: str
