# Multi-stage build para otimizar o tamanho da imagem
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar arquivos de configuração do npm
COPY package*.json ./
COPY tsconfig.json ./

# Instalar dependências
RUN npm ci --only=production && \
    npm install -D typescript @types/node

# Copiar código fonte TypeScript
COPY src-ts/ ./src-ts/

# Compilar TypeScript
RUN npm run build

# Imagem final (production)
FROM node:20-alpine

# Configurar timezone para America/Sao_Paulo
ENV TZ=America/Sao_Paulo
RUN apk add --no-cache tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

WORKDIR /app

# Copiar apenas o necessário da fase de build
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

# Copiar arquivos de configuração
COPY config/config.json ./config/config.json
COPY analise-dados/parametros_simulacao_upas.json ./analise-dados/parametros_simulacao_upas.json

# Criar diretório para logs
RUN mkdir -p /app/logs && \
    chown -R node:node /app

# Usar usuário não-root
USER node

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD node -e "console.log('ok')" || exit 1

# Executar o simulador
CMD ["node", "dist/index.js"]