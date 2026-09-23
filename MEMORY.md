# Antigravity Memory & Plan

## Goal
Tujuan utama: Menyelesaikan Setup Fase 0 dan beralih ke Fase 1 sesuai dengan `docs/06-RENCANA-FASE.md`. Bekerja secara otonom sementara pengguna sedang makan siang.

## Progress Checklist

### Fase 0 - Fondasi (MENGAMBIL ALIH)
- [x] P0-1: Inisialisasi Git + monorepo (`api/`, `web/`, `mobile/`, `face-service/`, `db/`, `docs/`, `prototype/`) dan salin berkas (Selesai di iterasi sebelumnya)
- [x] P0-2: Jalankan `db/01`–`db/04` di PostgreSQL. Ganti `new_id()` → `uuidv7()` (Selesai di iterasi sebelumnya)
- [x] P0-3: Pasang pgvector; jalankan `db/05`. (Baru saja diselesaikan, pgvector diinstal via docker exec, `05_face.sql` dijalankan tanpa galat)
- [x] P0-2b: Jadikan hasilnya baseline Alembic `0001`. (Sedang memproses setup Alembic)
- [x] P0-4: API: app factory FastAPI, `pydantic-settings`, logging JSON, seragam galat, dll.
- [x] P0-5: Docker: `Dockerfile` api, `docker-compose.yml`, dll.
- [x] P0-6: Web: Vite + TS strict, Tailwind + shadcn/ui.
- [ ] P0-7: Mobile: verifikasi flutter.
- [x] P0-8: Struktur folder (ESLint `eslint-plugin-boundaries`).
- [ ] P0-9: Kerangka lapisan backend.
- [x] P0-10: face-service `/health`.
- [x] P0-11: CI GitHub Actions dasar. (Selesai di iterasi sebelumnya)
- [x] P0-12: Webhook Discord `#vms-ci` & sanitize_for_discord(). (Selesai di iterasi sebelumnya)

### Catatan Penting
- Jangan membuat mock atau bypass terhadap RLS.
- Database yang digunakan adalah `100.117.92.14:5433` (Docker Postgis 16).
- Pengguna (Ageng) sedang istirahat sampai jam 13:00. Bekerja secara mandiri dan laporkan di akhir goal.
