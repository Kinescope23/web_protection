FROM node:20-alpine AS builder
WORKDIR /app

# Сначала зависимости — слой кэшируется и не пересобирается при правке кода.
# package-lock.json закоммичен, поэтому npm ci вместо npm install (воспроизводимо).
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

COPY . .
RUN npm run build

# ---------- Стадия выдачи: nginx (статика + прокси) ----------
FROM nginx:1.27-alpine

# healthcheck для docker compose (проверяет, что nginx отдаёт SPA)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO /dev/null http://localhost/ || exit 1

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]