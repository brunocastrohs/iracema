# Presentation/API/exception_handlers.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
import requests

from Presentation.API.error_response import make_error_response
from Application.helpers.exceptions import GeoServerError

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # detail do HTTPException pode ser str ou dict — normalizamos
        msg = exc.detail if isinstance(exc.detail, str) else "Erro HTTP na aplicação."
        extra = exc.detail if isinstance(exc.detail, dict) else None
        return make_error_response(
            status_code=exc.status_code,
            error="HTTPException",
            message=str(msg),
            exc=exc,
            extra=extra,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return make_error_response(
            status_code=422,
            error="ValidationError",
            message="Erro de validação de entrada.",
            exc=exc,
            extra={"errors": exc.errors()},
        )

    @app.exception_handler(GeoServerError)
    async def geoserver_exception_handler(request: Request, exc: GeoServerError):
        return make_error_response(
            status_code=502,  # Bad Gateway para upstream
            error="GeoServerError",
            message=exc.message,
            exc=exc,
            extra={
                "status_code": exc.status_code,
                "method": exc.method,
                "url": exc.url,
                "response_text": exc.response_text,
            },
        )

    @app.exception_handler(requests.HTTPError)
    async def requests_http_error_handler(request: Request, exc: requests.HTTPError):
        resp = exc.response
        extra = {}
        if resp is not None:
            extra.update({
                "status_code": resp.status_code,
                "url": str(resp.url),
                "response_text": resp.text[:2000] if resp.text else None,
            })
        return make_error_response(
            status_code=502,
            error="UpstreamHTTPError",
            message=str(exc),
            exc=exc,
            extra=extra,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return make_error_response(
            status_code=500,
            error="InternalServerError",
            message=str(exc) or "Erro interno não tratado.",
            exc=exc,
        )
