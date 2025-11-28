# Presentation/API/error_response.py
import traceback
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional

def make_error_response(
    *,
    status_code: int,
    error: str,
    message: str,
    exc: Optional[BaseException] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    payload: Dict[str, Any] = {
        "error": error,
        "message": message,
        "detail": traceback.format_exc() if exc else None,
    }
    if extra:
        payload.update(extra)
    return JSONResponse(status_code=status_code, content=payload)
