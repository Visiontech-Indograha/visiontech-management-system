# Absensi Hikvision lokal: pasang di server (milik pemilik)

Semua langkah di sini dijalankan PEMILIK di server `visiontech-bar` (192.168.88.160). Tidak ada yang otomatis. Tanda **[SUDO]** = butuh sudo.
Perangkat (DS-K1T343MX 192.168.88.13 dan 192.168.88.12) dan server satu LAN; tanpa VPN, tanpa Cloudflare/Tailscale.

## Gambaran
- Perangkat mengirim event ke `http://192.168.88.160:8088/hikvision/events/<token>` (HTTP polos, tanpa redirect).
- `vms_hik_proxy` (nginx, 32 MB, `deploy/hikvision/`) hanya menerima dari dua IP perangkat, POST saja, batas 2 MB dan 5 req/dtk/IP, lalu meneruskan ke API `127.0.0.1:8000/api/v1/hikvision/events/<token>`. API tetap memeriksa token (hash), IP perangkat, dan laju.
- Token disensor di log proxy (`/hikvision/events/***`) dan di log uvicorn (filter `app/core/log_sensor.py`, aktif setelah image API baru terpasang oleh autodeploy).
- Proxy tidak memakai Cloudflare Tunnel/Funnel/Tailscale Serve. Jangan tambahkan.

## Langkah 0: periksa port 8080/8081 (baca saja)
```
ss -ltnp | grep -E ':(8000|8001|8080|8081|8088)\b'
```
Compose beta di repo mengikat `127.0.0.1:8081`. Bila 8080/8081 tampil `0.0.0.0` atau `*`, compose prod/beta di server berbeda dari repo: catat dan laporkan ke arsitek (ufw/`tutup-port-layanan.sh` perlu ditinjau). Tidak dibahas lebih jauh di sini.
Pastikan juga `TRUSTED_PROXY_IPS` di `api.env` prod mencakup gateway Docker (bila IP perangkat tampak sebagai 172.x di API, token benar tetapi dijawab 404).

## Langkah 1: berkas proxy (tanpa sudo)
```
mkdir -p ~/deploy/hikvision && cd ~/deploy/hikvision
cp ~/deploy/vms-mvp/deploy/hikvision/{compose.yml,nginx.conf.template,.env.proxy.example,.env.hikvision.example,uji-konfigurasi.sh} .
cp .env.proxy.example .env.proxy && chmod 600 .env.proxy      # edit bila IP berbeda
bash uji-konfigurasi.sh .                                      # harus LULUS (nginx -t)
```

## Langkah 2: firewall [SUDO]
Port 8088 hanya dari dua perangkat (ufw aktif/tidak: cek `sudo ufw status` dulu).
```
sudo ufw status | head -n 5
sudo ufw allow from 192.168.88.13 to any port 8088 proto tcp
sudo ufw allow from 192.168.88.12 to any port 8088 proto tcp
```
Mundur: `sudo ufw delete allow from 192.168.88.13 to any port 8088 proto tcp` (dan .12). Catatan: port yang dipublikasikan Docker melewati ufw; proxy ini host network sehingga ufw berlaku.

## Langkah 3: nyalakan proxy
```
cd ~/deploy/hikvision && docker compose config -q && docker compose up -d
docker logs --tail 5 vms_hik_proxy
curl -s -o /dev/null -w '%{http_code}\n' http://192.168.88.160:8088/   # dari server: 403 (bukan perangkat)
```
Mundur: `docker compose down` (tanpa `-v`). Tidak mengubah stack prod.

## Langkah 4: kredensial perangkat (untuk tarik riwayat)
Berkas rahasia di server, tidak di Git, contoh: `deploy/hikvision/.env.hikvision.example`.
```
cp .env.hikvision.example ~/deploy/vms-mvp/.env.hikvision && chmod 600 ~/deploy/vms-mvp/.env.hikvision
nano ~/deploy/vms-mvp/.env.hikvision      # HIKVISION_<SERIAL>_USER / _PASS
```
`docker exec` tidak membaca berkas itu; teruskan lewat `--env-file` (baris cron di bawah). Jangan menempel nilai di riwayat shell atau chat.

## Langkah 5: cron (crontab pemilik; perintah dari kontainer `vms_api`)
Pasang dengan `crontab -e`. Sesuaikan `<SERIAL>`. Log ke `~/deploy/vms-mvp/logs/`.
```
*/5 * * * *  docker exec vms_api python -m app.cli hikvision-proses >> ~/deploy/vms-mvp/logs/hik-proses.log 2>&1
15 3 * * *   docker exec --env-file ~/deploy/vms-mvp/.env.hikvision vms_api python -m app.cli hikvision-tarik --perangkat <SERIAL> --dari "$(date -d '2 days ago' +\%F)" --jeda 1 >> ~/deploy/vms-mvp/logs/hik-tarik.log 2>&1
0 7 * * *    docker exec vms_api python -m app.cli pengingat-dokumen >> ~/deploy/vms-mvp/logs/pengingat-dokumen.log 2>&1
```
- `hikvision-proses`: ubah event mentah menjadi absen (aman diulang).
- `hikvision-tarik` harian dini hari: rekonsiliasi jendela 2 hari, idempoten; `--jeda 1` agar perangkat tidak terbebani. Ulangi baris untuk perangkat ke-2.
- `pengingat-dokumen`: lihat `deploy/PENGINGAT-DOKUMEN.md`.
Catatan: `hikvision-proses` belum ada di `app/cli.py` cabang `development` saat dokumen ini ditulis (PR terpisah); pasang baris cron-nya setelah PR itu masuk dan `--help` menampilkannya.
Mundur: hapus barisnya di `crontab -e`.

## Langkah 6: impor riwayat SATU KALI (jangan masuk cron)
Dry-run dulu (hanya menghitung dan mencari event tertua, tidak menyimpan), lalu nyata. Pakai `--lanjutkan` bila terputus.
```
docker exec --env-file ~/deploy/vms-mvp/.env.hikvision vms_api python -m app.cli hikvision-tarik --perangkat <SERIAL> --dry-run --jeda 1
docker exec --env-file ~/deploy/vms-mvp/.env.hikvision vms_api python -m app.cli hikvision-tarik --perangkat <SERIAL> --jeda 1
docker exec vms_api python -m app.cli hikvision-proses
```
Bawaan menarik sampai 366 hari ke belakang; batasi dengan `--dari 2026-01-01`. Jalankan di luar jam kerja. Cadangan DB harian (01:30) sudah ada; jalankan `deploy/backup.sh` dulu bila ingin titik pulih tepat sebelum impor. Mundur: tidak ada penghapusan otomatis; hubungi arsitek (jangan hapus baris tabel manual).

## Langkah 7: pemantauan
Event masuk (baca saja):
```
docker logs --since 1h vms_hik_proxy | tail -n 20            # baris: IP, POST /hikvision/events/***, status
docker logs --since 1h vms_hik_proxy | awk '{print $5}' | sort | uniq -c   # sebaran status (200 normal; 404 token/IP salah; 429 terlalu cepat)
docker exec vms_db_prod psql -U vms_app -d visiontech_db -Atc "select max(received_at), count(*) filter (where received_at > now() - interval '24 hours') from hikvision_event"
```
(Kueri hanya SELECT; kolom `received_at` dari migrasi v2_0040.)
Alarm bila tidak ada event 24 jam: tambahkan ke cron pemilik (Discord memakai webhook di `notify.env`, jangan ditaruh di baris cron):
```
30 8 * * *  n=$(docker exec vms_db_prod psql -U vms_app -d visiontech_db -Atc "select count(*) from hikvision_event where received_at > now() - interval '24 hours'"); [ "${n:-0}" -eq 0 ] && . ~/deploy/vms-mvp/notify.env && curl -s -H 'Content-Type: application/json' -d '{"content":"Hikvision: tidak ada event 24 jam terakhir"}' "$DISCORD_WEBHOOK_DEPLOY" >/dev/null
```
Alternatif: monitor Uptime Kuma tipe push. Akhir pekan/libur dapat memicu alarm palsu: abaikan atau gunakan hanya hari kerja (`1-5` di kolom hari).

## Catatan keamanan
- Token = rahasia: jangan dikutip di tiket/chat. Bila terlanjur bocor, buat ulang token di admin Hikvision dan ubah URL di perangkat.
- Bila log lama (sebelum filter terpasang) sudah memuat token di `docker logs vms_api`, putar token.
