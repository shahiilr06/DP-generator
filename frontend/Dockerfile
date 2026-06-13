# ── Frontend Dockerfile ────────────────────────────────────────────────────
# Multi-stage: builder runs Vite build, runner serves via nginx
# ───────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --silent

COPY . .
RUN npm run build

# ── Stage 2: runner (nginx) ──────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runner

# Remove default nginx placeholder
RUN rm -rf /usr/share/nginx/html/*

# Copy Vite build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx config (proxies /api → backend:8000)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
