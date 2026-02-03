from abc import ABC, abstractmethod
from Application.dto.iracema_query_plan_dto import QueryPlanArgsDto

class IIracemaFCClient(ABC):
    @abstractmethod
    def generate_query_plan(
        self,
        prompt_inicial_fc: str,
        question: str,
        columns_meta: list[dict],
        top_k: int,
    ) -> QueryPlanArgsDto:
        """
        Retorna QueryPlanArgsDto (validado).
        """
        raise NotImplementedError()
