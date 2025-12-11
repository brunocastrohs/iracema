# ============================
# 1) Imagem base
# ============================
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=docker

# Opcional: ajuste de timezone se quiser
# ENV TZ=America/Sao_Paulo

# ============================
# 2) Dependências de sistema
# ============================

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ============================
# 3) Diretório de trabalho
# ============================

WORKDIR /app

# ============================
# 4) Instalar dependências Python
# ============================

# Copiamos apenas o requirements primeiro pra aproveitar cache de build
COPY Presentation/API/requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# ============================
# 5) Copiar código da aplicação
# ============================

# Copia tudo (ajuste se preferir algo mais enxuto)
COPY . /app

# Se você precisar que o Python enxergue o pacote Presentation.*, configure PYTHONPATH
ENV PYTHONPATH=/app

# ============================
# 6) Expor porta da API
# ============================

EXPOSE 9090

# ============================
# 7) Comando de inicialização
# ============================

# Usa o mesmo entrypoint que você usa localmente
CMD ["uvicorn", "Presentation.API.main:app", "--host", "0.0.0.0", "--port", "9090"]
