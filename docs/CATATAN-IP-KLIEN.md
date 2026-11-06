# Catatan: IP klien di balik proxy (TRUSTED_PROXY_IPS)

Jalur: klien -> Tailscale Serve/Funnel (beta) atau Cloudflare Tunnel (prod) -> kontainer web (Caddy) -> API.

Aturan:
1. Caddy (`web/Caddyfile`) mempercayai `X-Forwarded-For` dari rentang privat dan 100.64.0.0/10, lalu menambahkan alamat peer di kanan. Tanpa itu header klien ditimpa dan API melihat IP Docker (mis. 172.20.0.5 atau gateway).
2. API (`client_ip()` di `api/app/core/rate_limit.py`) membaca XFF dari kanan hanya bila peer-nya ada di `TRUSTED_PROXY_IPS`. Hop tepercaya dilewati; hop pertama yang bukan tepercaya = klien.
3. `TRUSTED_PROXY_IPS` harus memuat SUBNET jaringan Docker compose lingkungan itu (bukan hanya gateway), karena peer API adalah kontainer web dan gateway muncul sebagai hop di XFF.

Nilai (isi di `api.env` server, bukan di Git):
- Beta: subnet jaringan `betanet` (cek: `docker network inspect <jaringan-beta> --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'`), contoh `172.20.0.0/16`.
- Prod: subnet jaringan compose prod (perintah sama), ditambah `127.0.0.1` bila ada proxy lokal.
- Aman memakai `172.16.0.0/12` (seluruh rentang bridge Docker) bila subnet bisa berubah; API tidak dipublikasikan langsung ke internet sehingga peer di rentang itu hanya kontainer sendiri.

Verifikasi: login dari HP/PC, buka Akun & keamanan > Perangkat yang masuk; IP harus alamat klien (mis. 100.x tailnet atau IP publik), bukan 172.x.
Tes otomatis: `api/tests/core/test_rate_limit.py` (rantai XFF) dan `api/tests/architecture/test_caddy_ip_klien.py`.
