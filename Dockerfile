# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    ENVIRONMENT=docker \
    PYTHONPATH=/app

WORKDIR /app

# Dependências do sistema (psycopg2-binary costuma funcionar sem build deps,
# mas esses pacotes ajudam com SSL/requests e compatibilidade de wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala
COPY Presentation/API/requirements.txt /app/Presentation/API/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install -r /app/Presentation/API/requirements.txt

# Copia o projeto inteiro (camadas: Application, Data, Domain, External, Presentation)
COPY . /app

# Garante o diretório do Chroma
# (no docker você configurou /app/.iracema/chroma)
RUN mkdir -p /app/.iracema/chroma \
 && chmod -R 755 /app/.iracema

# Porta padrão da API
EXPOSE 9090

# Healthcheck opcional (ajuste o path se quiser)
# Se não tiver endpoint de health, pode remover.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:9090/iracema-api/v1/start/catalog || exit 1

# Run
CMD ["uvicorn", "Presentation.API.main:app", "--host", "0.0.0.0", "--port", "9090"]
