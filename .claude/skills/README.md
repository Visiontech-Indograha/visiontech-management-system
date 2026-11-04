# Skill proyek VMS - indeks

Berkas ini adalah indeks. Aturan kerja lengkap ada di `docs/PANDUAN-AGENTIK.md`. Sub-agen (definisi) ada di `.claude/agents/`.

## 1. Skill proses (dibuat untuk peran agentik)

| Skill | Dipakai oleh | Isi singkat |
|---|---|---|
| `vms-architect` | arsitek (sesi utama), `architect` | memecah tugas, brief, tinjau PR, ADR, keputusan untuk klien, urutan rilis |
| `vms-qa` | `qa` | uji awam per peran, audit kebocoran GET-only, matriks peran x endpoint, uji HP (adb aman), uji web (Playwright), laporan |
| `vms-cicd-versioning` | arsitek, `devops-engineer`, semua engineer (konvensi commit) | cabang, workflow, gerbang, deploy, rollback, APK, versi, perbaikan CI |
| `vms-system-design` | arsitek, `api-engineer`, `db-engineer`, `devops-engineer` | kapasitas 4 GB, Big O sistem, caching, antrean, rate limit, idempotensi, RLS, observability |
| `vms-devops-infra` | arsitek, `devops-engineer` (WAJIB untuk tugas infrastruktur) | tata letak server prod dan beta, autodeploy dan rollback, Dockerfile dan Compose, rahasia, cadangan dan uji pulih, monitoring, runbook insiden, runner dan workflow yang dimatikan, keamanan jaringan, anti-pola dengan bukti berkas:baris |

## 2. Skill lapisan (ditulis agen lain; rujuk nama persis)

| Skill | Dipakai oleh | Status di worktree cabang ini |
|---|---|---|
| `vms-web` | `web-engineer` | ada (ditulis agen lain; belum ditinjau di sini) |
| `vms-mobile` | `mobile-engineer` | ada (ditulis agen lain; belum ditinjau di sini) |
| `vms-ux-design-system` | `web-engineer`, `mobile-engineer`, `qa`, arsitek | ada (ditulis agen lain; belum ditinjau di sini) |
| `vms-api` | `api-engineer` | ada (ditulis agen lain; belum ditinjau di sini) |
| `vms-db` | `api-engineer`, `db-engineer` | ada (ditulis agen lain; belum ditinjau di sini) |
| `vms-storage-minio` | `api-engineer`, `devops-engineer` | ada (ditulis agen lain; belum ditinjau di sini) |

Bila skill lapisan tidak ada saat sub-agen dijalankan, sub-agen harus melapor (bagian "Belum diuji / risiko"), bukan menebak aturannya.

## 3. Definisi sub-agen (`.claude/agents/`)

| Berkas | Peran | Model (frontmatter) |
|---|---|---|
| `architect.md` | arsitek | opus |
| `qa.md` | QA independen | sonnet |
| `web-engineer.md` | engineer web | sonnet |
| `mobile-engineer.md` | engineer mobile | sonnet |
| `api-engineer.md` | engineer API | sonnet |
| `db-engineer.md` | engineer basis data | sonnet |
| `devops-engineer.md` | engineer DevOps | sonnet |

## 4. Peta skill global (dari daftar skill sesi ini)

Skill global tidak disalin ke repo. Pakai bila sesuai tugas. Yang bertanda "wajib" berasal dari instruksi sistem atau aturan proyek.

| Skill global | Kapan dipakai di proyek VMS |
|---|---|
| `modern-web-guidance:modern-web-guidance` | WAJIB untuk tugas HTML/CSS/JS sisi klien (web-engineer) sebelum mengubah kode. |
| `postman:api-engineer` | mendesain atau menguji endpoint API; memandu ke skill Postman lain. |
| `postman:api-testing` | uji endpoint atau koleksi assertion (uji kontrak API oleh api-engineer atau qa). Gunakan Postman CLI yang terpasang (CLAUDE.md). |
| `postman:api-documentation` | menerbitkan dokumentasi API dari OpenAPI. |
| `postman:ai-readiness` | menilai kesiapan API untuk agen. |
| `postman:ci-integration` | menambah uji API ke CI (perubahan `ci.yml` oleh devops-engineer, atas persetujuan arsitek). |
| `postman:variables` | memisahkan rahasia dan variabel lingkungan untuk koleksi Postman. |
| `security-review` | (perintah `/security-review`) tinjauan keamanan perubahan pada cabang sebelum PR ke `prod`. |
| `code-review` | (perintah `/code-review`) tinjauan kebenaran diff atau PR; dipakai arsitek saat tinjau. Mode `max`/`ultra` hanya bila pemilik meminta. |
| `simplify` | merapikan kode yang sudah berubah (kualitas, bukan bug). Dipakai engineer sebelum lapor. |
| `update-config` | mengubah `settings.json` (izin, hook, env). Dipakai arsitek atau pemilik; bukan engineer. |
| `fewer-permission-prompts` | menyusun daftar izin baca-saja di `.claude/settings.json` untuk mengurangi prompt. |
| `run` | menjalankan aplikasi nyata untuk melihat perubahan (web dev 5173, API 8000). Dipakai qa dan engineer. |
| `claude-in-chrome` / `anthropic-skills:chrome-browser` | uji UI di Chrome pengguna (tab sendiri, tutup setelah selesai). Pilihan QA selain Playwright. |
| `anthropic-skills:built-in-browser` | uji UI di browser panel aplikasi desktop Claude. |
| `dataviz` | membuat grafik atau dasbor di web (warna, aksesibilitas). |
| `loop`, `schedule` | tugas berulang (mis. pantau deploy). Jangan dipakai untuk mengubah server tanpa perintah. |
| `anthropic-skills:skill-creator` | membuat atau menguji skill baru atau memperbaiki deskripsi skill. |
| `init` | membuat CLAUDE.md baru. Jangan dipakai di repo ini tanpa perintah (CLAUDE.md sudah ada di root sumber). |
| `plugin-authoring` | membuat mod untuk antarmuka Claude. Tidak dipakai untuk produk VMS. |
| `claude-api` | referensi API Claude/Anthropic. Tidak dipakai untuk fitur produk VMS kecuali ada integrasi LLM yang diminta. |
| `anthropic-skills:docx`, `pdf`, `xlsx`, `pptx`, `docs` | berkas dokumen kantor. Fitur ekspor VMS dibuat di API, bukan lewat skill ini. |

## 5. Aturan penamaan dan versi skill

- Nama folder = nilai `name:` di frontmatter SKILL.md. Huruf kecil, tanda hubung, tanpa spasi.
- Skill proyek memakai awalan `vms-`. Skill proses: `vms-<area>` (architect, qa, cicd-versioning, system-design). Skill lapisan: `vms-<lapisan>` (web, mobile, api, db, ux-design-system, storage-minio).
- Sub-agen: nama berkas = nilai `name:` (kata benda peran: architect, qa, web-engineer, dst.).
- Deskripsi (`description:`) ditulis dengan kata kunci tugas, supaya skill terpanggil di waktu yang tepat. Hindari deskripsi yang tumpang tindih antar skill.
- Versi skill: tulis di baris pertama bagian "Riwayat" di akhir SKILL.md (format `vX.Y - tanggal - perubahan`). Naikkan `Y` untuk tambahan aturan, `X` bila aturan lama berubah. Frontmatter Claude Code tidak memakai kolom versi.
- Pemilik skill proses: arsitek. Pemilik skill lapisan: agen yang menulisnya, atas persetujuan arsitek.
- Setiap skill harus merujuk berkas sumber (kode, workflow, dokumen) untuk klaim faktual. Klaim tanpa sumber ditandai.

## 6. Pemeliharaan

- Perbarui skill saat: aturan proyek berubah (CLAUDE.md), workflow CI berubah, ADR baru disetujui, atau sebuah kejadian menunjukkan aturan kurang (post-mortem singkat).
- Tinjau semua skill proses saat menutup satu fase (lihat `vms-next/docs/07`, "Cara kerja per fase").
- Jangan menyimpan rahasia, sandi, atau data pribadi di skill.
