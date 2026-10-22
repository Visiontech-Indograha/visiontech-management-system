"""Uji skenario lapangan nyata lewat API (docs/37 §10): order klien → survei → persiapan → instalasi → BAST.

CCTV & ACS bekerja di lokasi yang sama ("MGT Minas") dan saling tunggu: kabel ACS ditarik lewat galian parit tim
CCTV (prasyarat lintas divisi), scaffolding dipasang di 5 titik CCTV, galian 69 m butuh 3 hari (rollover).
Tanggal bisnis digeser dengan PUT /system/dev-clock (hanya APP_ENV bukan production) — server harus berjalan.

    cd api
    .venv/Scripts/python.exe ../scripts/uji_skenario_minas.py [YYYY-MM-DD senin minggu survei]
"""
from __future__ import annotations

import io
import random
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw

BASE = "http://127.0.0.1:8000/api/v1"
PM = "budisantoso@visiontech.id"
TL = {"CCTV": "zulkifli@visiontech.id", "ACS": "yudisetiawan@visiontech.id",
      "Electrical": "ekoprasetyo@visiontech.id", "Wall Display": "hendragunawan@visiontech.id"}
DIVISION = {"CCTV": "Divisi CCTV & Keamanan Elektronik", "ACS": "Divisi Access Control System (ACS)",
            "Electrical": "Divisi Electrical & Arus Kuat", "Wall Display": "Divisi Wall Display & LED Screen"}
OUT = Path(__file__).resolve().parent.parent / "docs" / "bukti-e2e"
PASSWORD = "secret"
MOBILE_UA = "VisiontechVMS/9.9 (build 9; Android SDK 34; uji-skenario)"
SITE = {"name": "MGT Minas", "lat": 0.79015, "lng": 101.4466}
CLIENT = "PT. Pertamina Hulu Rokan"
MONDAY = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 11, 2)

http = httpx.Client(timeout=120)
log: list[str] = []
_tokens: dict[str, str] = {}


def day(n: int) -> date:
    return MONDAY + timedelta(days=n)


def login(email: str, mobile: bool) -> str:
    headers = {"User-Agent": MOBILE_UA} if mobile else {}
    body = {"email": email, "password": PASSWORD, **({"platform": "mobile"} if mobile else {})}
    r = http.post(f"{BASE}/auth/login", json=body, headers=headers)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


def as_(who: str) -> dict[str, str]:
    if who not in _tokens:
        _tokens[who] = login(PM if who == "PM" else TL[who], mobile=who != "PM")
    h = {"Authorization": f"Bearer {_tokens[who]}"}
    if who != "PM":
        h["User-Agent"] = MOBILE_UA
    return h


def call(who: str, method: str, path: str, expect: int | tuple[int, ...] = (200, 201), label: str = "", **kw: Any) -> Any:
    r = http.request(method, f"{BASE}{path}", headers=as_(who), **kw)
    ok = r.status_code in ((expect,) if isinstance(expect, int) else expect)
    msg = f"{'OK ' if ok else 'GAGAL'} [{who}] {label or path} → {r.status_code}"
    if not ok or r.status_code >= 400:
        try:
            msg += f" · {r.json().get('error', {}).get('message') or r.text[:200]}"
        except ValueError:
            msg += f" · {r.text[:200]}"
    print(msg)
    log.append(msg)
    if not ok:
        raise SystemExit(f"\nBerhenti: {label or path} (harapan {expect}, dapat {r.status_code})")
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else r.content


def clock(d: date) -> None:
    got = call("PM", "PUT", "/system/dev-clock", json={"day": d.isoformat()}, label=f"jam simulasi → {d}")
    assert got["today"] == d.isoformat()


def photo(who: str, text: str) -> str:
    """Foto uji unik (dedup SHA-256 server) dengan teks penanda."""
    img = Image.new("RGB", (640, 480), tuple(random.randint(40, 200) for _ in range(3)))
    d = ImageDraw.Draw(img)
    for _ in range(30):
        x, y = random.randint(0, 600), random.randint(0, 440)
        d.rectangle((x, y, x + 40, y + 40), fill=tuple(random.randint(0, 255) for _ in range(3)))
    d.text((20, 20), text, fill="white")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return call(who, "POST", "/files/upload", files={"file": (f"{text}.jpg", buf.getvalue(), "image/jpeg")},
                label=f"unggah foto {text}")["file_id"]


def work_types() -> dict[tuple[str, str], dict[str, Any]]:
    rows = call("PM", "GET", "/work-types", label="daftar work type")
    return {(w["division_name"], w["name"]): w for w in rows}


def item_photos(who: str, wt: dict[str, Any], tag: str) -> list[dict[str, str]]:
    return [{"file_id": photo(who, f"{tag} {s['label']}"), "requirement_id": s["id"]} for s in wt["photos"]]


def start_day(who: str, plan_id: str) -> None:
    call(who, "POST", f"/work-plans/daily/{plan_id}/start", label=f"ketua mulai jadwal {plan_id[:8]}")


def main() -> None:
    me = call("PM", "GET", "/auth/me", label="profil PM")
    divisions = {d["name"]: d for d in call("PM", "GET", "/divisions", label="daftar divisi")}
    div = {k: divisions[name]["id"] for k, name in DIVISION.items()}
    teams = {t["division_id"]: t for t in call("PM", "GET", "/work-plans/form-options", label="opsi form")["teams"]}
    team = {k: teams[v]["team_id"] for k, v in div.items()}
    wts = work_types()
    W = {
        "CCTV": {n: wts[("Divisi CCTV & Keamanan Elektronik", n)] for n in
                 ("Survei CCTV", "Pemasangan Scaffolding", "Galian Parit", "Instalasi CCTV")},
        "ACS": {n: wts[("Divisi Access Control System (ACS)", n)] for n in
                ("Survei ACS", "Penarikan Kabel ACS", "Instalasi ACS Pintu")},
    }
    run = MONDAY.isoformat()

    # ── 1. PM menerima pekerjaan dari klien → order per divisi ────────────────
    clock(day(-3))
    order = {}
    for k, title in (("CCTV", "Pemasangan 5 Unit CCTV MGT Minas"), ("ACS", "Pemasangan ACS & Barrier Gate MGT Minas")):
        order[k] = call("PM", "POST", "/work-completions", label=f"order klien {k}", json={
            "division_id": div[k], "pm_id": me.get("employee_id"), "client_name": CLIENT, "project_title": title,
            "order_number": f"WO-{k}-{run}", "total_target_unit": 5, "unit_measure": "Titik",
            "priority_level": "NORMAL", "site_address": SITE["name"], "site_lat": SITE["lat"], "site_lng": SITE["lng"],
            "summary_notes": f"Permintaan klien: {title}."})["completion_id"]

    # ── 2. Jadwal survei minggu 1 (Senin) untuk kedua tim ────────────────────
    def plan(k: str, d: date) -> str:
        p = call("PM", "POST", "/work-plans/daily", label=f"jadwal {k} {d}", json={
            "division_id": div[k], "team_id": team[k], "work_date": d.isoformat(), "site_name": SITE["name"],
            "site_lat": SITE["lat"], "site_lng": SITE["lng"], "attendance_radius_m": 300,
            "clock_in_time": "07:00", "clock_out_time": "16:00"})
        return p["daily_plan_id"]

    def item(k: str, plan_id: str, wt: str, title: str, phase: str, qty: float = 1, dep: str | None = None,
             expect: int | tuple[int, ...] = 201) -> Any:
        return call("PM", "POST", f"/work-plans/daily/{plan_id}/items", expect=expect, label=f"item {k}: {title}",
                    json={"work_type_id": W[k][wt]["id"], "title": title, "task_phase": phase,
                          "completion_id": order[k], "target_qty": qty, "location_name": SITE["name"],
                          "depends_on_item_id": dep, "is_main_deliverable": phase in ("INSTALLATION",)})

    def approve(plan_id: str) -> None:
        call("PM", "POST", f"/work-plans/daily/{plan_id}/approve", label=f"PM terbitkan {plan_id[:8]}")

    survey_plan, survey_task = {}, {}
    for k in ("CCTV", "ACS"):
        survey_plan[k] = plan(k, day(0))
        survey_task[k] = item(k, survey_plan[k], f"Survei {k}", f"Survei {k} MGT Minas", "SURVEY")["item_id"]
        approve(survey_plan[k])

    # ── 3. Hari survei: ketua tim mengisi titik di lapangan ───────────────────
    clock(day(0))
    for k in ("CCTV", "ACS"):
        start_day(k, survey_plan[k])
        s = call(k, "GET", f"/work-plans/surveys/{survey_task[k]}", label=f"buka survei {k}")
        types = {t["name"]: t for t in s["point_types"]}
        if k == "CCTV":
            points = [(f"Titik CCTV {i:02d}", "Titik Kamera CCTV", "PROPOSED", ["Scaffolding"] + (["Galian"] if i <= 2 else []),
                       [("CCTV PTZ Outdoor", 1, "Unit"), ("Kabel STP", 25 + i * 3, "Meter")]) for i in range(1, 6)]
        else:
            points = [(f"Pintu Akses {i}", "Pintu Akses", "PROPOSED", [], [("Reader Multiclass", 1, "Unit"),
                       ("Magnetic Lock", 1, "Pasang"), ("Kabel ACS", 30, "Meter")]) for i in range(1, 4)]
            points += [("Pintu Emergency Gudang", "Pintu Emergency + Alarm", "EXISTING", [], [("Sirine", 1, "Unit")]),
                       ("Barrier Gate Pos 1", "Barrier Gate", "PROPOSED", ["Galian"],
                        [("Barrier Gate Motor", 1, "Unit"), ("Kabel Loop", 20, "Meter"),
                         (f"Tiang Reader Custom {run}", 1, "Unit")])]  # material di luar katalog
        for n, (name, tname, status, needs, mats) in enumerate(points):
            t = types[tname]
            call(k, "POST", f"/work-plans/surveys/{survey_task[k]}/points", label=f"titik {name} ({tname})", json={
                "name": name, "point_type_id": t["work_type_id"], "point_status": status,
                "remarks": [f"Kondisi {name}: aman, akses kendaraan ada."],
                "photos": [{"file_id": photo(k, f"{name} {sl['name']}"), "requirement_id": sl["requirement_id"]}
                           for sl in t["slots"]],
                "lines": [{"category": "MATERIAL", "name": m, "qty": q, "unit": u} for m, q, u in mats]
                         + [{"category": "KEBUTUHAN", "name": nd, "qty": 1, "unit": "Lot"} for nd in needs],
                "site_lat": SITE["lat"] + 0.0002 * n, "site_lng": SITE["lng"] + 0.00025 * n})
        call(k, "POST", f"/work-plans/surveys/{survey_task[k]}/lines", label=f"material umum {k}",
             json={"name": "Rack 19 inch" if k == "CCTV" else "Panel ACS Utama", "qty": 1, "unit": "Unit"})
        call(k, "POST", f"/work-plans/surveys/{survey_task[k]}/submit", label=f"kirim survei {k}")
        call(k, "POST", f"/work-plans/daily/{survey_plan[k]}/complete", label=f"tutup jadwal survei {k}")

    # ── 4. PM meninjau: sesuaikan BoM, simpan material baru ke katalog, setujui ─
    s = call("PM", "GET", f"/work-plans/surveys/{survey_task['ACS']}", label="PM buka survei ACS")
    assert s["can_edit_bom"], "PM harus bisa mengubah BoM saat meninjau"
    custom = [(p, ln) for p in s["points"] for ln in p["lines"] if ln["custom"]]
    assert custom, "material di luar katalog harus ditandai"
    p, ln = custom[0]
    call("PM", "PUT", f"/work-plans/surveys/lines/{ln['bom_id']}", label="PM ubah qty material custom",
         json={"name": ln["name"], "qty": 2, "unit": ln["unit"]})
    call("PM", "POST", f"/work-plans/surveys/{survey_task['ACS']}/catalog", label="PM simpan ke katalog",
         json={"point_type_id": p["point_type_id"], "name": ln["name"], "unit": ln["unit"]})
    for k in ("CCTV", "ACS"):
        call("PM", "POST", f"/work-plans/surveys/{survey_task[k]}/review", label=f"PM setujui survei {k}",
             json={"decision": "APPROVE"})
        call("PM", "GET", f"/exports/surveys/{survey_task[k]}/preview", label=f"pratinjau laporan survei {k}")
        call("PM", "POST", f"/exports/surveys/{survey_task[k]}", label=f"laporan survei resmi {k}")
    call("PM", "PUT", f"/work-plans/surveys/lines/{ln['bom_id']}", expect=409, label="BoM terkunci setelah disetujui",
         json={"name": ln["name"], "qty": 3, "unit": ln["unit"]})

    # ── 5. Minggu 2: persiapan (scaffolding 5 titik, galian parit 3 hari) ─────
    prep = call("PM", "POST", f"/work-plans/surveys/{survey_task['CCTV']}/plan", label="rencana scaffolding 5 titik",
                json={"work_date": day(7).isoformat(), "work_type_id": W["CCTV"]["Pemasangan Scaffolding"]["id"],
                      "task_phase": "PREPARATION"})
    cctv_w2 = prep["daily_plan_id"]
    galian = item("CCTV", cctv_w2, "Galian Parit", "Galian parit jalur kabel 69 m", "PREPARATION", 69)["item_id"]
    approve(cctv_w2)
    # ACS minggu 3: kabel ACS menunggu galian CCTV (prasyarat lintas divisi), lalu instalasi dari survei.
    acs_w3 = call("PM", "POST", f"/work-plans/surveys/{survey_task['ACS']}/plan", label="rencana instalasi ACS (bawaan jenis titik)",
                  json={"work_date": day(14).isoformat()})["daily_plan_id"]
    opts = call("PM", "GET", f"/work-plans/daily/{acs_w3}/prerequisite-options", label="calon prasyarat ACS")
    assert any(o["item_id"] == galian and o["other_team"] for o in opts), "galian CCTV harus muncul sebagai calon prasyarat"
    kabel = item("ACS", acs_w3, "Penarikan Kabel ACS", "Tarik kabel ACS di parit CCTV", "INSTALLATION", 1,
                 dep=galian)["item_id"]
    approve(acs_w3)
    cctv_w3 = call("PM", "POST", f"/work-plans/surveys/{survey_task['CCTV']}/plan", label="rencana instalasi CCTV",
                   json={"work_date": day(14).isoformat(), "work_type_id": W["CCTV"]["Instalasi CCTV"]["id"]})["daily_plan_id"]
    approve(cctv_w3)

    # Hari 1 galian: scaffolding selesai, galian baru 25 m → rollover ke besok
    clock(day(7))
    start_day("CCTV", cctv_w2)
    items = call("CCTV", "GET", f"/work-plans/daily/{cctv_w2}/items", label="item persiapan CCTV")
    for it in items:
        if it["item_id"] == galian:
            continue
        call("CCTV", "PATCH", f"/work-plans/items/{it['item_id']}/progress", label=f"selesai {it['title']}",
             json={"completed_qty": it["target_qty"],
                   "photos": item_photos("CCTV", W["CCTV"]["Pemasangan Scaffolding"], it["title"])})
    call("CCTV", "PATCH", f"/work-plans/items/{galian}/progress", label="galian hari 1: 25 m", json={"completed_qty": 25})
    call("CCTV", "POST", f"/work-plans/items/{galian}/request-rollover", label="ketua minta rollover galian",
         json={"delay_reason": "Tanah keras & hujan sore, galian baru 25 m.", "completed_qty": 25})
    call("PM", "POST", f"/work-plans/items/{galian}/rollover-decision", label="PM setujui rollover ke hari 2",
         json={"approve": True, "target_date": day(8).isoformat(), "note": "Lanjut besok."})
    call("CCTV", "POST", f"/work-plans/daily/{cctv_w2}/complete", label="tutup jadwal CCTV hari 1")

    def continuation(origin: str) -> dict[str, Any]:
        chain = call("PM", "GET", f"/work-plans/items/{origin}/chain", label="rantai rollover galian")
        return chain[-1]

    g2 = continuation(galian)
    clock(day(8))
    start_day("CCTV", g2["daily_plan_id"])
    call("CCTV", "PATCH", f"/work-plans/items/{g2['item_id']}/progress", label="galian hari 2: 25 m",
         json={"completed_qty": 25})
    # ACS mencoba lebih awal (galian CCTV belum selesai) → progres kabel ditolak.
    acs_early = plan("ACS", day(8))
    early = item("ACS", acs_early, "Penarikan Kabel ACS", "Tarik kabel ACS tahap awal", "INSTALLATION", 1,
                 dep=galian)["item_id"]
    approve(acs_early)
    start_day("ACS", acs_early)
    call("ACS", "PATCH", f"/work-plans/items/{early}/progress", expect=409,
         label="ACS tarik kabel sebelum galian CCTV selesai (harus ditolak)", json={"completed_qty": 1})
    call("CCTV", "POST", f"/work-plans/items/{g2['item_id']}/request-rollover", label="rollover galian ke hari 3",
         json={"delay_reason": "Ketemu pipa eksisting, galian manual.", "completed_qty": 25})
    call("PM", "POST", f"/work-plans/items/{g2['item_id']}/rollover-decision", label="PM setujui rollover ke hari 3",
         json={"approve": True, "target_date": day(9).isoformat()})
    call("CCTV", "POST", f"/work-plans/daily/{g2['daily_plan_id']}/complete", label="tutup jadwal CCTV hari 2")

    g3 = continuation(galian)
    assert float(g3["target_qty"]) == 19, f"sisa galian harus 19 m, dapat {g3['target_qty']}"

    # ── 6. Minggu 3 dicoba lebih awal: ACS belum boleh menarik kabel ──────────
    # (jadwal ACS minggu 3 baru dimulai di tanggalnya; cek prasyarat dilakukan saat progres)
    clock(day(9))
    start_day("CCTV", g3["daily_plan_id"])
    call("CCTV", "PATCH", f"/work-plans/items/{g3['item_id']}/progress", label="galian hari 3: sisa 19 m selesai",
         json={"completed_qty": 19, "photos": item_photos("CCTV", W["CCTV"]["Galian Parit"], "galian")})
    call("CCTV", "POST", f"/work-plans/daily/{g3['daily_plan_id']}/complete", label="tutup jadwal CCTV hari 3")
    # Galian sudah selesai → kabel ACS tahap awal (yang tadi ditolak) boleh diselesaikan, jadwalnya ditutup.
    call("ACS", "PATCH", f"/work-plans/items/{early}/progress", label="kabel ACS tahap awal selesai setelah galian",
         json={"completed_qty": 1, "photos": item_photos("ACS", W["ACS"]["Penarikan Kabel ACS"], "kabel awal")})
    call("ACS", "POST", f"/work-plans/daily/{acs_early}/complete", label="tutup jadwal ACS tahap awal")

    # ── 7. Minggu 3: instalasi CCTV & ACS (kabel ACS menunggu galian → sudah selesai) ─
    clock(day(14))
    for k, pid, wt in (("CCTV", cctv_w3, W["CCTV"]["Instalasi CCTV"]), ("ACS", acs_w3, None)):
        start_day(k, pid)
        for it in call(k, "GET", f"/work-plans/daily/{pid}/items", label=f"item instalasi {k}"):
            t = wt or next(w for w in wts.values() if w["id"] == it["work_type_id"])
            call(k, "PATCH", f"/work-plans/items/{it['item_id']}/progress", label=f"selesai {it['title']}",
                 json={"completed_qty": it["target_qty"], "photos": item_photos(k, t, it["title"])})
        call(k, "POST", f"/work-plans/daily/{pid}/complete", label=f"tutup jadwal instalasi {k}")
    assert any(i["item_id"] == kabel and i["status"] == "DONE"
               for i in call("ACS", "GET", f"/work-plans/daily/{acs_w3}/items", label="cek kabel ACS")), \
        "kabel ACS harus DONE setelah galian CCTV selesai"

    # ── 8. Work completion: BAST ketua → PM sahkan → order selesai → dokumen ─
    clock(day(21))
    sig = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    for k in ("CCTV", "ACS"):
        call(k, "POST", f"/work-completions/{order[k]}/sign", label=f"ketua tanda tangan BAST {k}", json={
            "signature_data_url": sig, "summary_notes": f"Pekerjaan {k} MGT Minas selesai sesuai survei.",
            "obstacles": "Galian 3 hari karena tanah keras & pipa eksisting." if k == "CCTV" else None,
            "realization_photos": [photo(k, f"realisasi {k} {i}") for i in (1, 2)]})
        call("PM", "POST", f"/work-completions/{order[k]}/sign", label=f"PM sahkan BAST {k}",
             json={"signature_data_url": sig})
        # Pengesahan PM otomatis menutup order (COMPLETED) dan menguncinya.
        assert call("PM", "GET", f"/work-completions/{order[k]}", label=f"order {k} selesai")["order_status"] == "COMPLETED"
        call("PM", "PATCH", f"/work-completions/{order[k]}/status", expect=409, label=f"order {k} terkunci",
             json={"order_status": "ONGOING"})
        for tpl in ("BAST", "BAST_PDF", "BOQ", "PROGRESS_SLIDES", "SURVEY_REPORT"):
            # BAST_PDF butuh WeasyPrint+GTK (ada di image Docker); di Windows tanpa GTK server menjawab 503.
            call("PM", "POST", f"/exports/work-completions/{order[k]}", label=f"ekspor {tpl} {k}",
                 expect=(200, 201, 503) if tpl == "BAST_PDF" else (200, 201), json={"template": tpl})
        o = call("PM", "GET", f"/work-completions/{order[k]}", label=f"cek order {k}")
        names = {b["material_name"] for b in o.get("bom_items") or []}
        assert not names & {"Scaffolding", "Galian"}, f"BoQ {k} tercemar baris KEBUTUHAN: {names}"
        if o.get("signature_hash"):
            call("PM", "GET", f"/verify/work-completions/{order[k]}", params={"h": o["signature_hash"]},
                 label=f"verifikasi QR {k}")
    call("PM", "POST", "/exports/periodic", label="rekap periodik CCTV minggu 1–4", json={
        "division_id": div["CCTV"], "start_date": day(0).isoformat(), "end_date": day(21).isoformat()})

    rutin_dan_bukti(me, div, team, wts, order, survey_task)
    call("PM", "PUT", "/system/dev-clock", json={"day": None}, label="jam kembali normal")
    print(f"\nSELESAI: {sum(m.startswith('OK') for m in log)} langkah OK")


# Pekerjaan rutin di hari kerja yang belum terisi alur Minas: (kode tim) → daftar (jenis, lokasi, lat, lng, jumlah hari)
ROUTINE = {
    "CCTV": [("Maintenance CCTV", "Kantor Rumbai", 0.6153, 101.4012, 0), ("Replacement CCTV", "Gudang Duri", 1.2852, 101.2312, 0)],
    "ACS": [("Maintenance ACS", "Kantor Rumbai", 0.6153, 101.4012, 0), ("Replacement ACS", "Pos Jaga Dumai", 1.6652, 101.4471, 0)],
    "Electrical": [("Instalasi Electrical", "Gedung Workshop Minas", 0.7861, 101.4511, 6),
                   ("Maintenance Electrical", "Kantor Rumbai", 0.6153, 101.4012, 0),
                   ("Replacement Electrical", "Panel Gudang Duri", 1.2852, 101.2312, 0)],
    "Wall Display": [("Instalasi Wall Display", "Ruang Kontrol Duri", 1.2869, 101.2290, 6),
                     ("Maintenance Wall Display", "Lobby Kantor Rumbai", 0.6150, 101.4015, 0),
                     ("Replacement Wall Display", "Ruang Rapat Minas", 0.7905, 101.4470, 0)],
}
SIG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


def save(sub: str, name: str, content: bytes) -> None:
    path = OUT / f"skenario-{MONDAY.isoformat()}" / sub / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def export(path: str, body: dict[str, Any] | None, sub: str, name: str, label: str,
           expect: tuple[int, ...] = (200, 201)) -> None:
    r = http.post(f"{BASE}{path}", json=body, headers=as_("PM"))
    ok = r.status_code in expect
    msg = f"{'OK ' if ok else 'GAGAL'} [PM] {label} → {r.status_code}"
    print(msg)
    log.append(msg)
    if not ok:
        raise SystemExit(f"Berhenti: {label}")
    if r.status_code < 300:
        save(sub, name, r.content)


def rutin_dan_bukti(me: dict[str, Any], div: dict[str, str], team: dict[str, str], wts: dict[Any, Any],
                    minas_order: dict[str, str], survey_task: dict[str, str]) -> None:
    """Isi setiap hari kerja (Senin–Sabtu, 4 minggu) keempat tim, selesaikan sampai BAST, lalu kumpulkan dokumen."""
    workdays = [day(n) for n in range(0, 26) if day(n).weekday() < 6]
    clock(day(-3))
    taken: dict[str, set[date]] = {}
    for k in TL:
        rows = call("PM", "GET", "/work-plans/daily", label=f"jadwal yang sudah ada {k}", params={
            "start": day(0).isoformat(), "end": day(27).isoformat(), "division_id": div[k]})
        taken[k] = {date.fromisoformat(r["work_date"]) for r in rows}
    orders: dict[str, list[tuple[str, str]]] = {}  # tim → [(order_id, judul)]
    todo: list[tuple[date, str, str]] = []  # (tanggal, tim, daily_plan_id)
    for k, jobs in ROUTINE.items():
        free = [d for d in workdays if d not in taken[k]]
        if not free:
            continue
        oids = []
        for wt_name, site, lat, lng, _ in jobs:
            title = f"{wt_name} — {site}"
            oid = call("PM", "POST", "/work-completions", label=f"order klien {title}", json={
                "division_id": div[k], "pm_id": me.get("employee_id"), "client_name": CLIENT, "project_title": title,
                "order_number": f"WO-{k[:4].upper()}-{wt_name.split()[0][:4].upper()}-{MONDAY:%y%m%d}",
                "total_target_unit": 1, "unit_measure": "Lot", "priority_level": "NORMAL",
                "site_address": site, "site_lat": lat, "site_lng": lng,
                "summary_notes": f"Permintaan klien: {title}."})["completion_id"]
            oids.append(oid)
            orders.setdefault(k, []).append((oid, title))
        # Instalasi bertahap dulu (n hari), lalu Maintenance & Replacement bergantian.
        sched: list[int] = []
        for j, job in enumerate(jobs):
            sched += [j] * job[4]
        rest = [j for j, job in enumerate(jobs) if job[4] == 0]
        while len(sched) < len(free):
            sched.append(rest[len(sched) % len(rest)])
        for n, d in enumerate(free):
            j = sched[n]
            wt_name, site, lat, lng, _ = jobs[j]
            pid = call("PM", "POST", "/work-plans/daily", label=f"jadwal {k} {d} {site}", json={
                "division_id": div[k], "team_id": team[k], "work_date": d.isoformat(), "site_name": site,
                "site_lat": lat, "site_lng": lng, "attendance_radius_m": 300,
                "clock_in_time": "07:00", "clock_out_time": "16:00"})["daily_plan_id"]
            phase = wt_name.split()[0].upper().replace("INSTALASI", "INSTALLATION")
            step = sum(1 for x in sched[:n + 1] if x == j)
            call("PM", "POST", f"/work-plans/daily/{pid}/items", label=f"item {k}: {wt_name} hari ke-{step}", json={
                "work_type_id": wts[(DIVISION[k], wt_name)]["id"], "title": f"{wt_name} {site} (hari ke-{step})",
                "task_phase": phase, "completion_id": oids[j], "target_qty": 1, "location_name": site,
                "is_main_deliverable": True})
            call("PM", "POST", f"/work-plans/daily/{pid}/approve", label=f"PM terbitkan {k} {d}")
            todo.append((d, k, pid))

    for d in sorted({t[0] for t in todo}):
        clock(d)
        for _, k, pid in [t for t in todo if t[0] == d]:
            start_day(k, pid)
            for it in call(k, "GET", f"/work-plans/daily/{pid}/items", label=f"item {k} {d}"):
                wt = next(w for w in wts.values() if w["id"] == it["work_type_id"])
                call(k, "PATCH", f"/work-plans/items/{it['item_id']}/progress", label=f"selesai {it['title']}",
                     json={"completed_qty": it["target_qty"], "photos": item_photos(k, wt, it["title"]),
                           "notes": "Pekerjaan selesai, perangkat diuji normal."})
            call(k, "POST", f"/work-plans/daily/{pid}/complete", label=f"tutup jadwal {k} {d}")

    # BAST semua order rutin (Sabtu minggu ke-4)
    clock(day(26))
    for k, lst in orders.items():
        for oid, title in lst:
            call(k, "POST", f"/work-completions/{oid}/sign", label=f"ketua tanda tangan BAST {title}", json={
                "signature_data_url": SIG, "summary_notes": f"{title} selesai.",
                "realization_photos": [photo(k, f"realisasi {title}")]})
            call("PM", "POST", f"/work-completions/{oid}/sign", label=f"PM sahkan BAST {title}",
                 json={"signature_data_url": SIG})

    # ── Bukti: dokumen per order, laporan harian, laporan mingguan (PPTX) ────
    all_orders = [(k, oid, title) for k, lst in orders.items() for oid, title in lst] + [
        (k, oid, f"Minas {k}") for k, oid in minas_order.items()]
    ext = {"BAST": "docx", "BOQ": "xlsx", "PROGRESS_SLIDES": "pptx", "SURVEY_REPORT": "docx", "BAST_PDF": "pdf"}
    for k, oid, title in all_orders:
        sub = f"order/{k}/{title.replace('/', '-').replace(' — ', ' - ')}"
        for tpl in ("BAST", "BAST_PDF", "BOQ", "PROGRESS_SLIDES"):
            export(f"/exports/work-completions/{oid}", {"template": tpl}, sub, f"{tpl}.{ext[tpl]}",
                   f"dokumen {tpl} · {title}", expect=(200, 201, 503) if tpl == "BAST_PDF" else (200, 201))
    for k, task in survey_task.items():
        export(f"/exports/surveys/{task}", None, f"order/{k}/Minas {k}", "Laporan Survei.docx",
               f"laporan survei resmi {k}")
    for k in TL:
        for d in workdays:
            export("/exports/periodic", {"division_id": div[k], "start_date": d.isoformat(),
                                         "end_date": d.isoformat(), "export_format": "EXCEL_XLSX"},
                   f"harian/{k}", f"{d.isoformat()}.xlsx", f"laporan harian {k} {d}")
        for w in range(4):
            export("/exports/periodic", {"division_id": div[k], "start_date": day(7 * w).isoformat(),
                                         "end_date": day(7 * w + 5).isoformat(), "export_format": "PPTX"},
                   f"mingguan/{k}", f"Minggu {w + 1} ({day(7 * w):%d %b}-{day(7 * w + 5):%d %b}).pptx",
                   f"laporan mingguan {k} minggu {w + 1}")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            http.put(f"{BASE}/system/dev-clock", json={"day": None}, headers=as_("PM"))
        except Exception:  # noqa: BLE001
            pass
