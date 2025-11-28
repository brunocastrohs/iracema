# Presentation/API/controllers/auth_controller.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import jwt  # PyJWT

from Presentation.API.settings import settings

router = APIRouter()

# ---- modelos ----
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos

# ---- config JWT (com defaults seguros p/ dev) ----
JWT_SECRET: str = getattr(settings, "JWT_SECRET", "fauno_dev_secret_change_me")
JWT_ISSUER: str = getattr(settings, "JWT_ISSUER", "Fauno")
JWT_AUDIENCE: str = getattr(settings, "JWT_AUDIENCE", "FaunoClient")
JWT_EXPIRES_MINUTES: int = getattr(settings, "JWT_EXPIRES_MINUTES", 120)
JWT_ALG: str = "HS256"

# ---- endpoint ----
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    # valida credenciais fixas
    if not (body.email.lower() == "fauno@admin.br" and body.password == "00cc00cc"):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=JWT_EXPIRES_MINUTES)

    payload = {
        "sub": str(body.email).lower(),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "roles": ["admin"],  # opcional
        "app": "fauno",
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return TokenResponse(
        access_token=token,
        expires_in=JWT_EXPIRES_MINUTES * 60,
    )
