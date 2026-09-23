# Tahap 1: build Vite. Tahap 2: Caddy menyajikan static + proxy /api (D-14).
FROM node:24-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Nama harus sama dengan yang dibaca kode (import.meta.env.VITE_API_BASE_URL).
# Kosong = same-origin; Caddy meneruskan /api ke api:8000.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=builder /app/dist /srv
EXPOSE 80 443
