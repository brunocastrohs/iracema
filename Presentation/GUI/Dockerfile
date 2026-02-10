# ---------- Etapa 1: Build ----------
FROM node:20-alpine AS builder
WORKDIR /app

# Instalar deps de forma determinística
COPY package*.json ./
RUN npm ci

# Copiar código
COPY . .

# (opcional) garantir .env.production presente
# COPY .env.production .env.production

# (opcional) variáveis embedadas no build do Vite
ARG VITE_API_BASE_URL

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL


# Build (Vite em modo production)
RUN npm run build


# ---------- Etapa 2: Runtime (Nginx servindo estáticos) ----------
FROM nginx:alpine AS runner

# Copia a configuração do Nginx (veja nginx.conf abaixo)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia o build
COPY --from=builder /app/dist /usr/share/nginx/html/iracema

# (opcional) healthcheck simples
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -qO- http://127.0.0.1/ || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
