# Application/exceptions.py
from typing import Optional

class GeoServerError(Exception):
    def __init__(self, *, status_code: int, method: str, url: str, response_text: str | None, message: str):
        self.status_code = status_code
        self.method = method
        self.url = url
        self.response_text = (response_text or "")[:2000]
        self.message = message
        super().__init__(f"{message} [{method} {url}] (HTTP {status_code}) :: {self.response_text}")

    def __str__(self) -> str:
        base = f"{self.message} [{self.method} {self.url}] (HTTP {self.status_code})"
        if self.response_text:
            base += f" :: {self.response_text[:2000]}"  # limita para evitar payloads enormes
        return base


class ServiceError(Exception):
    """Erro de serviço interno (domínio), para encapsular erros de etapas do fluxo."""
    pass
