// P9-1 · Uji beban k6 — jam sibuk pagi: 60 pekerja lapangan bersamaan (K-02: ≤ 60 bersamaan, ≤ 400 absen/hari).
// Data: tests/beban/seed_beban.py (organisasi SINTETIS di DB uji). Jangan pernah diarahkan ke prod.
//
//   k6 run -e BASE_URL=http://127.0.0.1:8000 -e AKUN=akun.json -e BEBAN_PASSWORD=… -e FOTO=swafoto.jpg beban.js
//
// Per pekerja (VU): login HP → beranda (/auth/me, /sites, /work-plans, /attendance, /notifications)
// → ±30% di luar radius: unggah swafoto (JPEG ukuran foto HP, dikompresi server) + penjelasan → absen masuk
// → menjelajah ±5 menit (jeda 5–15 dtk) → absen pulang. Ditambah 1 PM yang membuka daftar absensi berkala.
// Lulus: p95 < 2 dtk (docs/09 §ambang peringatan) dan galat < 1%.
import http from "k6/http";
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";
import exec from "k6/execution";

const BASE = `${__ENV.BASE_URL || "http://127.0.0.1:8000"}/api/v1`;
const PASSWORD = __ENV.BEBAN_PASSWORD;
const DATA = JSON.parse(open(__ENV.AKUN || "akun.json"));
const FIELD = new SharedArray("lapangan", () => DATA.field);
const PHOTO = new Uint8Array(open(__ENV.FOTO || "swafoto.jpg", "b"));

// Foto unik per pekerja: penanda VU setelah penanda akhir JPEG (diabaikan dekoder). Tanpa ini semua VU mengirim
// berkas yang sama → deduplikasi SHA-256 lintas pekerja, yang tidak terjadi pada swafoto sungguhan.
function photoFor(vu) {
  const tag = `|vu-${vu}`;
  const out = new Uint8Array(PHOTO.length + tag.length);
  out.set(PHOTO);
  for (let i = 0; i < tag.length; i++) out[PHOTO.length + i] = tag.charCodeAt(i);
  return out.buffer;
}

function report(name, r) {
  if (r.status !== 200 && r.status !== 0) console.warn(`${name} ${r.status}: ${String(r.body).slice(0, 200)}`);
}
const BROWSE_SECONDS = Number(__ENV.JELAJAH_DETIK || 300);

export const options = {
  scenarios: {
    lapangan: {
      executor: "per-vu-iterations", exec: "fieldWorker", vus: FIELD.length, iterations: 1,
      startTime: "0s", maxDuration: "15m",
    },
    pm: { executor: "constant-vus", exec: "projectManager", vus: 1, duration: `${BROWSE_SECONDS + 60}s` },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
    "http_req_duration{name:login}": ["p(95)<2000"],
    "http_req_duration{name:check-in}": ["p(95)<2000"],
    "http_req_duration{name:upload}": ["p(95)<3000"],   // kompresi foto: ambang docs/13 (p95 3 dtk)
  },
};

function login(email, platform) {
  let r;
  for (let attempt = 0; attempt < 3; attempt++) {   // seperti aplikasi: koneksi gagal → coba lagi
    r = http.post(`${BASE}/auth/login`, JSON.stringify({ email, password: PASSWORD, platform }),
      { headers: { "Content-Type": "application/json" }, tags: { name: "login" } });
    if (r.status !== 0) break;
    sleep(2);
  }
  check(r, { "login 200": (x) => x.status === 200 });
  return { Authorization: `Bearer ${r.json("access_token")}`, "Content-Type": "application/json" };
}

function get(path, headers, name) {
  const r = http.get(`${BASE}${path}`, { headers, tags: { name } });
  check(r, { [`${name} 200`]: (x) => x.status === 200 });
  return r;
}

function home(headers) {
  get("/auth/me", headers, "me");
  get("/sites", headers, "sites");
  get("/work-plans", headers, "work-plans");
  get("/attendance", headers, "attendance");
  get("/notifications", headers, "notifications");
}

export function fieldWorker() {
  // Indeks per skenario (0..59): __VU dibagi dengan skenario PM sehingga satu akun bisa terpakai dua kali.
  const email = FIELD[exec.scenario.iterationInTest];
  sleep(Math.random() * 60);                       // datang dalam 1 menit pertama
  const headers = login(email, "mobile");
  home(headers);

  const outside = Math.random() < 0.3;
  const body = { site_id: DATA.site_id, accuracy_m: 12,
                 location: { lat: DATA.site.lat + (outside ? 0.005 : 0.0002), lng: DATA.site.lng } };
  if (outside) {
    const up = http.post(`${BASE}/files/upload`, { file: http.file(photoFor(__VU), "swafoto.jpg", "image/jpeg") },
      { headers: { Authorization: headers.Authorization }, tags: { name: "upload" } });
    check(up, { "upload 200": (x) => x.status === 200 });
    body.selfie_file_id = up.json("file_id");
    body.explanation = "Survei titik di luar lokasi (uji beban)";
  }
  const ci = http.post(`${BASE}/attendance/check-in`, JSON.stringify(body), { headers, tags: { name: "check-in" } });
  check(ci, { "check-in 200": (x) => x.status === 200 });
  report("check-in", ci);

  const until = Date.now() + BROWSE_SECONDS * 1000;
  while (Date.now() < until) {
    sleep(5 + Math.random() * 10);
    home(headers);
  }
  const co = http.post(`${BASE}/attendance/check-out`, JSON.stringify({ location: body.location }),
    { headers, tags: { name: "check-out" }, responseCallback: http.expectedStatuses(200, 409) });
  // Absen di luar radius menunggu pemeriksaan PM → pulang ditolak 409 (aturan R-33), bukan galat beban.
  check(co, { "check-out 200/409": (x) => x.status === 200 || x.status === 409 });
  if (co.status !== 409) report("check-out", co);
}

let pmHeaders = null;
export function projectManager() {
  if (!pmHeaders) pmHeaders = login(DATA.pm, "web");
  get("/attendance?status=NEEDS_REVIEW", pmHeaders, "pm-attendance");
  get("/work-plans", pmHeaders, "work-plans");
  sleep(10);
}
