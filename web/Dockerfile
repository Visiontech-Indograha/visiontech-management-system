# Tahap 1: build Vite. Tahap 2: Caddy menyajikan static + proxy /api (D-14).
FROM node:24-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY . .
# Nama harus sama dengan yang dibaca kode (import.meta.env.VITE_API_BASE_URL).
# Kosong = same-origin; Caddy meneruskan /api ke api:8000.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
# Penanda lingkungan: "beta" untuk build beta; kosong (produksi) = tanpa penanda.
ARG VITE_APP_ENV=""
ENV VITE_APP_ENV=${VITE_APP_ENV}
RUN npm run build

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=builder /app/dist /srv
# Metadata citra (terbaca lewat `docker inspect` / deploy/status-layanan.sh). GIT_SHA & VMS_ENV diisi autodeploy.sh.
ARG GIT_SHA=tidak-diketahui
ARG VMS_ENV=tidak-diketahui
LABEL org.opencontainers.image.title="vms-web"       org.opencontainers.image.description="VMS Web (React + Caddy, meneruskan /api ke API)"       org.opencontainers.image.revision="${GIT_SHA}"       org.opencontainers.image.source="https://github.com/Visiontech-Indograha/visiontech-management-system"       vms.layanan="web"       vms.lingkungan="${VMS_ENV}"       vms.port-dalam="80"

EXPOSE 80 443
