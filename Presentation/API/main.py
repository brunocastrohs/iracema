# Presentation/API/main.py

#Buildar
#python3 -m venv .venv && source .venv/bin/activate
#pip install -r Presentation/API/requirements.txt
#export ENVIRONMENT=dev PYTHONPATH=$PWD
#sudo mkdir -p /var/lib/iracema/chroma && sudo chown -R $USER:$USER /var/lib/iracema && sudo chmod -R 755 /var/lib/iracema
#uvicorn Presentation.API.main:app --host 0.0.0.0 --port 9090 --reload


#UNINSTALL
#pip uninstall -y langchain langchain-core langchain-community langchain-openai openai
#pip cache purge

#AUX
#nvidia-smi
#htop
#ollama pull qwen2.5:7b-q4
#ollama pull phi3
#ollama pull tinyllama


#Rodar
#source .venv/bin/activate && uvicorn Presentation.API.main:app --host 0.0.0.0 --port 9090 --reload

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Presentation.API.settings import settings
from Presentation.API.controllers.auth_controller import router as auth_router
from Presentation.API.controllers.ask_controller import router as ask_router
from Presentation.API.controllers.start_controller import router as start_router

app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

# CORS a partir do settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Rotas com prefixo do settings
app.include_router(auth_router, prefix=f"{settings.API_PREFIX}/auth", tags=["Auth"])
app.include_router(ask_router, prefix=f"{settings.API_PREFIX}/chat", tags=["Iracema"])
app.include_router(start_router, prefix=f"{settings.API_PREFIX}/start", tags=["Iracema"])



if __name__ == "__main__":
    env = os.getenv("ENVIRONMENT", "dev").lower()
    reload_flag = settings.API_RELOAD_ON_DEV and env != "docker"
    uvicorn.run(
        "Presentation.API.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=reload_flag,
    )
