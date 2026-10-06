"""
Pengenalan wajah untuk absensi HP — alur nyata di PostgreSQL (docs/06 fase 8, docs/08 §6).

Face-service dipalsukan (`FakeFace`); seluruh basis data, RLS, trigger, dan fungsi pencocokan asli. Yang dijaga:
- persetujuan biometrik wajib, bisa ditarik, dan menarik langsung menonaktifkan template;
- pendaftaran: 3-5 foto, liveness lolos, satu wajah per foto, pose konsisten, wajah milik karyawan lain ditolak;
- hasil cocok/tidak dihitung SERVER dari gambar wajah sementara (bukan dari klaim HP); hasil bermasalah menaikkan
  absensi ke Perlu review, tidak pernah menolak diam-diam; probe sekali pakai dan tidak kedaluwarsa;
- luring: hash gambar wajah terikat payload bertanda tangan; "cocok di HP, tidak di server" ditandai;
- face-service mati: absen tetap jalan (SKIPPED) lalu diperiksa ulang; tantangan TIDAK pernah lolos otomatis;
- pencocokan berjalan benar di bawah RLS dengan role `vms_app` (pemeriksaan "lebih mirip karyawan lain" butuh definer);
- gambar wajah yang lewat masa simpan dihapus (objek penyimpanan, baris, dan rujukan).
"""
from __future__ import annotations

import hashlib
import io
import json

import psycopg2
import pytest
from PIL import Image

from app.api.deps import get_face_embed_client
from app.crud.crud_face import vector_literal
from app.main import app
from app.services import face_service as fs
from app.services.face_embed_client import EmbedResult, FaceServiceUnavailable
from tests.conftest import World, _sync_conn, requires_db, sync_query
from tests.test_attendance_offline import INSIDE, Phone

pytestmark = requires_db

PASSED = {"challenges": ["bawah", "kiri"], "passed": True}   # klaim HP: hanya dipercaya untuk absen LURING
FAILED = {"challenges": ["bawah", "kiri"], "passed": False}
ME, OTHER, STRANGER = 10, 20, 30   # identitas tiruan: R pada piksel (0,0) gambar uji


def vec(person: int, shot: int = 0) -> list[float]:
    """Embedding tiruan 512-d: orang sama beda foto ≈ 0,997; orang berbeda ≈ 0."""
    v = [0.0] * 512
    v[person] = 1.0
    v[300 + shot % 100] = 0.05
    norm = sum(x * x for x in v) ** 0.5
    return [x / norm for x in v]


def png(person: int, shot: int = 0, pad: int = 0) -> bytes:
    """Gambar uji: identitas di piksel (0,0). `pad` menambah ukuran berkas (uji batas 5 MB)."""
    img = Image.new("RGB", (48, 48), (person, shot, 0))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue() + (b"\0" * pad)


class FakeFace:
    """Tiruan face-service: tanpa model; perilaku diatur uji."""

    def __init__(self) -> None:
        self.down = False
        self.faces: int | None = None
        self.quality = 0.9
        self.challenge: dict = {"status": "sukses", "detail": "ok", "quality": 0.9}
        self.stored: dict[str, bytes] = {}

    async def embed(self, image: bytes, filename: str = "probe.jpg") -> EmbedResult:
        if self.down:
            raise FaceServiceUnavailable("uji")
        if self.faces is not None and self.faces != 1:
            return EmbedResult(self.faces, None, None, None, "w600k_mbf", "buffalo_s")
        r, g, _ = Image.open(io.BytesIO(image)).convert("RGB").getpixel((0, 0))
        return EmbedResult(1, vec(r, g), self.quality, 0.99, "w600k_mbf", "buffalo_s")

    async def check_challenge(self, image: bytes, challenge: str, filename: str = "frame.jpg") -> dict:
        if self.down:
            raise FaceServiceUnavailable("uji")
        return self.challenge


@pytest.fixture
def face(monkeypatch):
    fake = FakeFace()
    app.dependency_overrides[get_face_embed_client] = lambda: fake
    monkeypatch.setattr(fs, "upload_file", lambda name, data, ct: fake.stored.__setitem__(name, data) or True)
    monkeypatch.setattr(fs, "get_object_bytes", lambda name: fake.stored.get(name))
    monkeypatch.setattr(fs, "delete_object", lambda name: fake.stored.pop(name, None) is not None or True)
    fs._template_hits.clear()
    fs._challenge_hits.clear()
    try:
        yield fake
    finally:
        app.dependency_overrides.pop(get_face_embed_client, None)


# ── pembantu alur ───────────────────────────────────────────────────
def consent(client, world: World, who: str = "member", state: str = "GRANTED"):
    headers = world.headers(client, who)
    version = client.get("/face/policy", headers=headers).json()["version"]
    return client.post("/face/consent", headers=headers, json={"state": state, "policy_version": version})


def proven(client, world: World, who: str = "member", challenges=("bawah", "kiri")) -> dict:
    """Liveness yang dipercaya server: bukti bertanda tangan dari /face/challenge-check, satu per tantangan lolos."""
    proofs = []
    for challenge in challenges:
        got = client.post("/face/challenge-check", headers=world.headers(client, who), data={"challenge": challenge},
                          files={"file": ("f.png", png(ME), "image/png")})
        assert got.status_code == 200 and got.json()["status"] == "sukses", got.text
        proofs.append(got.json()["proof"])
    return {"challenges": list(challenges), "passed": True, "proofs": proofs}


def enroll(client, world: World, who: str = "member", person: int = ME, shots=(1, 2, 3), live=None):
    live = live if live is not None else proven(client, world, who)
    files = [("files", (f"pose{i}.png", png(person, s), "image/png")) for i, s in enumerate(shots)]
    return client.post("/face/enroll", headers=world.headers(client, who), files=files,
                       data={"liveness": json.dumps(live)})


def enrolled(client, world: World, who: str = "member", person: int = ME) -> None:
    assert consent(client, world, who).status_code == 200
    done = enroll(client, world, who, person)
    assert done.status_code == 200, done.text


def probe(client, world: World, who: str = "member", person: int = ME, shot: int = 9, live=None, data: bytes | None = None):
    live = live if live is not None else proven(client, world, who)
    return client.post("/face/probe", headers=world.headers(client, who),
                       files={"file": ("wajah.png", data if data is not None else png(person, shot), "image/png")},
                       data={"liveness": json.dumps(live)})


def probe_id(client, world: World, who: str = "member", person: int = ME, shot: int = 9, live=None) -> str:
    made = probe(client, world, who, person, shot, live)
    assert made.status_code == 200, made.text
    return made.json()["probe_id"]


def check_in(client, world: World, who: str = "member", pid: str | None = None, **extra):
    body = {"site_id": world.site_id, "location": {"lat": INSIDE[0], "lng": INSIDE[1]}, **extra}
    if pid:
        body["face_probe_id"] = pid
    return client.post("/attendance/check-in", headers=world.headers(client, who), json=body)


def check_out(client, world: World, who: str = "member", pid: str | None = None):
    body = {"location": {"lat": INSIDE[0], "lng": INSIDE[1]}, **({"face_probe_id": pid} if pid else {})}
    return client.post("/attendance/check-out", headers=world.headers(client, who), json=body)


def att(world: World, who: str = "member") -> tuple:
    return sync_query(
        "SELECT status::text, face_result::text, face_similarity, check_out_face_result::text, selfie_file_id "
        "FROM vms.attendance WHERE employee_id = %s ORDER BY check_in_at DESC LIMIT 1", (world.employees[who],))[0]


# ── persetujuan & pendaftaran ─────────────────────────────────────────────
def test_policy_status_and_consent_rules(client, world, face):
    headers = world.headers(client, "member")
    policy = client.get("/face/policy", headers=headers).json()
    assert policy["version"] and "HANYA untuk absensi" in policy["text"]

    status = client.get("/face/status", headers=headers).json()
    assert status["employee_linked"] and status["consent"] is None and status["enrolled"] is False

    stale = client.post("/face/consent", headers=headers, json={"state": "GRANTED", "policy_version": "1999-01-01"})
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "POLICY_OUTDATED"

    assert consent(client, world).status_code == 200
    assert client.get("/face/status", headers=headers).json()["consent"] == "GRANTED"
    # Teks yang tersimpan milik SERVER, bukan kiriman klien.
    stored = sync_query("SELECT purpose_text FROM vms.biometric_consent WHERE employee_id = %s",
                        (world.employees["member"],))[0][0]
    assert stored == policy["text"]


def test_enrollment_required_flag_follows_server_setting(client, world, face, monkeypatch):
    from app.core.config import settings
    headers = world.headers(client, "member")
    monkeypatch.setattr(settings, "FACE_ENROLLMENT_REQUIRED", False)
    assert client.get("/face/status", headers=headers).json()["enrollment_required"] is False   # bawaan aman untuk produksi

    monkeypatch.setattr(settings, "FACE_ENROLLMENT_REQUIRED", True)
    assert client.get("/face/status", headers=headers).json()["enrollment_required"] is True    # belum setuju & belum daftar
    enrolled(client, world)
    assert client.get("/face/status", headers=headers).json()["enrollment_required"] is False
    assert consent(client, world, state="WITHDRAWN").status_code == 200                          # tarik persetujuan → wajib lagi
    assert client.get("/face/status", headers=headers).json()["enrollment_required"] is True


def test_admin_is_never_locked_by_required_enrollment(client, world, face, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "FACE_ENROLLMENT_REQUIRED", True)
    admin = client.get("/face/status", headers=world.headers(client, "admin")).json()
    member = client.get("/face/status", headers=world.headers(client, "member")).json()
    assert admin["employee_linked"] and admin["enrollment_required"] is False    # jalur darurat administrator
    assert member["enrollment_required"] is True


def test_enroll_validates_consent_liveness_and_images(client, world, face):
    assert enroll(client, world).json()["error"]["code"] == "CONSENT_REQUIRED"
    assert consent(client, world).status_code == 200

    assert enroll(client, world, shots=(1, 2)).status_code == 422                         # kurang dari 3 foto
    too_many = enroll(client, world, shots=(1, 2, 3, 4, 5, 6))
    assert too_many.status_code == 422                                                    # lebih dari 5 foto
    no_live = enroll(client, world, live=FAILED)
    assert no_live.status_code == 422 and "tantangan" in no_live.json()["error"]["message"].lower()
    claim_only = enroll(client, world, live=PASSED)                                       # klaim HP tanpa bukti server
    assert claim_only.status_code == 422 and "tantangan" in claim_only.json()["error"]["message"].lower()

    face.faces = 0
    assert "tidak terdeteksi" in enroll(client, world).json()["error"]["message"]
    face.faces = 2
    assert "lebih dari satu wajah" in enroll(client, world).json()["error"]["message"]
    face.faces = None
    face.quality = 0.05
    assert "terlalu buram" in enroll(client, world).json()["error"]["message"]
    face.quality = 0.9

    mixed = client.post("/face/enroll", headers=world.headers(client, "member"),
                        data={"liveness": json.dumps(proven(client, world))},
                        files=[("files", ("a.png", png(ME, 1), "image/png")),
                               ("files", ("b.png", png(OTHER, 2), "image/png")),
                               ("files", ("c.png", png(STRANGER, 3), "image/png"))])
    assert mixed.status_code == 422 and "bukan wajah yang sama" in mixed.json()["error"]["message"]

    bad_json = client.post("/face/enroll", headers=world.headers(client, "member"), data={"liveness": "{bukan json"},
                           files=[("files", (f"{i}.png", png(ME, i), "image/png")) for i in range(3)])
    assert bad_json.status_code == 422                                                    # bukan 500

    done = enroll(client, world)
    assert done.status_code == 200 and done.json()["enrolled"] == 3
    status = client.get("/face/status", headers=world.headers(client, "member")).json()
    assert status["enrolled"] and status["enrollment_version"] and status["model_name"] == "w600k_mbf"

    again = enroll(client, world, shots=(4, 5, 6))                                         # daftar ulang mengganti
    assert again.status_code == 200
    active = sync_query("SELECT count(*) FROM vms.face_enrollment WHERE employee_id = %s AND is_active",
                        (world.employees["member"],))[0][0]
    assert active == 3


def test_face_already_registered_by_another_employee_is_rejected_without_naming(client, world, face):
    enrolled(client, world, "member", ME)
    assert consent(client, world, "leader").status_code == 200
    dup = enroll(client, world, "leader", ME, shots=(5, 6, 7))
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "FACE_ALREADY_ENROLLED"
    assert "member" not in dup.text and "Karyawan uji" not in dup.text
    assert enroll(client, world, "leader", OTHER).status_code == 200                       # wajah berbeda diterima


def test_withdrawing_consent_deactivates_embeddings_at_once(client, world, face):
    enrolled(client, world)
    headers = world.headers(client, "member")
    assert client.get("/face/template", headers=headers).status_code == 200
    assert consent(client, world, state="WITHDRAWN").status_code == 200
    assert sync_query("SELECT count(*) FROM vms.face_enrollment WHERE employee_id = %s AND is_active",
                      (world.employees["member"],))[0][0] == 0
    status = client.get("/face/status", headers=headers).json()
    assert status["consent"] == "WITHDRAWN" and status["enrolled"] is False
    assert client.get("/face/template", headers=headers).json()["error"]["code"] == "CONSENT_REQUIRED"
    assert probe(client, world).json()["error"]["code"] == "CONSENT_REQUIRED"


def test_template_is_own_only_and_rate_limited(client, world, face):
    enrolled(client, world, "member", ME)
    enrolled(client, world, "leader", OTHER)
    mine = client.get("/face/template", headers=world.headers(client, "member")).json()
    assert len(mine["embeddings"]) == 3 and all(len(e) == 512 for e in mine["embeddings"])
    assert mine["model_name"] == "w600k_mbf" and mine["expires_at"]
    # Template pemilik lain berbeda: isinya milik akun yang meminta.
    theirs = client.get("/face/template", headers=world.headers(client, "leader")).json()
    assert mine["embeddings"][0] != theirs["embeddings"][0]
    for _ in range(9):
        assert client.get("/face/template", headers=world.headers(client, "member")).status_code == 200
    assert client.get("/face/template", headers=world.headers(client, "member")).status_code == 429


def test_face_collection_also_works_for_office_workers_on_web(client, world, face):
    """Pekerja kantor (absen lewat web) memakai wajah yang sama; yang dibatasi hanya jalur luring (milik HP)."""
    sync_query("UPDATE vms.employee SET attendance_mode = 'OFFICE' WHERE id = %s", (world.employees["finance"],))
    office = str(sync_query(
        "INSERT INTO vms.site (organization_id, name, location, radius_m) "
        "VALUES (%s, 'Kantor uji', ST_GeogFromText('POINT(106.8 -6.2)'), 100) RETURNING id", (world.org_id,))[0][0])
    headers = world.headers(client, "finance")
    enrolled(client, world, "finance")
    assert client.get("/face/template", headers=headers).status_code == 200
    assert client.get("/face/status", headers=headers).json()["enrolled"] is True

    def web_in(**extra):
        return client.post("/attendance/check-in", headers=headers, json={
            "channel": "WEB", "site_id": office, "location": {"lat": -6.2, "lng": 106.8}, "accuracy_m": 30, **extra})

    ok = web_in(face_probe_id=probe_id(client, world, "finance"))
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "AUTO_VALID" and ok.json()["face_result"] == "MATCH"
    out = client.post("/attendance/check-out", headers=headers, json={
        "channel": "WEB", "location": {"lat": -6.2, "lng": 106.8}})
    assert out.status_code == 200, out.text
    assert out.json()["status"] == "NEEDS_REVIEW"                                      # pulang tanpa wajah → periksa
    sync_query("DELETE FROM vms.attendance WHERE employee_id = %s", (world.employees["finance"],))

    missing = web_in()                                                                 # sudah terdaftar tapi tanpa wajah
    assert missing.status_code == 200, missing.text
    assert missing.json()["status"] == "NEEDS_REVIEW" and missing.json()["face_result"] == "SKIPPED"


def test_depan_is_guidance_only_and_never_issues_a_proof(client, world, face):
    got = client.post("/face/challenge-check", headers=world.headers(client, "member"), data={"challenge": "depan"},
                      files={"file": ("f.png", png(ME), "image/png")})
    assert got.status_code == 200 and got.json()["status"] == "sukses"
    assert got.json()["proof"] is None                       # foto diam lolos "lurus"; tidak boleh jadi bukti liveness


# ── gambar wajah sementara (probe) & tantangan ──────────────────────────────
def test_probe_rules_and_storage(client, world, face):
    assert probe(client, world).json()["error"]["code"] == "CONSENT_REQUIRED"
    assert consent(client, world).status_code == 200

    face.faces = 0
    assert "tidak terdeteksi" in probe(client, world).json()["error"]["message"]
    face.faces = 2
    assert "lebih dari satu wajah" in probe(client, world).json()["error"]["message"]
    face.faces = None
    face.quality = 0.02
    assert "terlalu buram" in probe(client, world).json()["error"]["message"]
    face.quality = 0.9

    assert probe(client, world, data=png(ME, pad=5 * 1024 * 1024 + 10)).status_code == 413
    assert probe(client, world, data=b"bukan gambar").status_code == 415
    bad_live = client.post("/face/probe", headers=world.headers(client, "member"), data={"liveness": "[1,2]"},
                           files={"file": ("w.png", png(ME), "image/png")})
    assert bad_live.status_code == 422

    made = probe(client, world, shot=4)
    assert made.status_code == 200 and made.json()["pending"] is False and made.json()["quality"] == 0.9
    row = sync_query("SELECT embedding IS NOT NULL, encode(sha256,'hex'), file_id FROM vms.face_probe WHERE id = %s",
                     (made.json()["probe_id"],))[0]
    assert row[0] and row[1] == hashlib.sha256(png(ME, 4)).hexdigest()                    # byte ASLI, tanpa kompresi
    key = sync_query("SELECT storage_key FROM vms.file_object WHERE id = %s", (row[2],))[0][0]
    assert "/face-probe/" in key and face.stored[key] == png(ME, 4)


def test_challenge_check_never_passes_without_face_service(client, world, face):
    headers = world.headers(client, "member")

    def frame(challenge: str):
        return client.post("/face/challenge-check", headers=headers, data={"challenge": challenge},
                           files={"file": ("f.png", png(ME), "image/png")})

    ok = frame("bawah")
    assert ok.status_code == 200 and ok.json()["status"] == "sukses"
    face.challenge = {"status": "menunggu", "detail": "Mulut kurang terbuka!"}
    waiting = frame("buka_mulut").json()
    assert waiting["status"] == "menunggu" and "Mulut" in waiting["detail"]
    assert frame("terbang").status_code == 422                                              # tantangan tak dikenal
    face.down = True
    down = frame("bawah")
    assert down.status_code == 503 and down.json()["error"]["code"] == "FACE_SERVICE_UNAVAILABLE"   # BUKAN sukses


# ── absen masuk & pulang ber-wajah (online) ─────────────────────────────────
def test_check_in_with_matching_face_is_valid_without_photo(client, world, face):
    enrolled(client, world)
    pid = probe_id(client, world)
    done = check_in(client, world, pid=pid)
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["face_result"] == "MATCH" and body["face_similarity"] > 0.9 and body["selfie_file_id"] is None
    assert att(world)[0] == "AUTO_VALID"
    check = sync_query("SELECT result::text, attendance_event, attendance_id IS NOT NULL, probe_file_id IS NOT NULL "
                       "FROM vms.face_check WHERE claimed_employee_id = %s", (world.employees["member"],))
    assert check == [("MATCH", "CHECK_IN", True, True)]
    assert sync_query("SELECT consumed_at IS NOT NULL, consumed_event FROM vms.face_probe WHERE id = %s", (pid,)) == [
        (True, "CHECK_IN")]


def test_probe_is_single_use(client, world, face):
    enrolled(client, world)
    pid = probe_id(client, world)
    assert check_in(client, world, pid=pid).status_code == 200
    again = check_out(client, world, pid=pid)
    assert again.status_code == 409 and again.json()["error"]["code"] == "PROBE_USED"


def test_other_persons_face_goes_to_review_not_rejected(client, world, face):
    enrolled(client, world)
    done = check_in(client, world, pid=probe_id(client, world, person=STRANGER))
    assert done.status_code == 200
    assert done.json()["face_result"] == "NO_MATCH" and done.json()["status"] == "NEEDS_REVIEW"


def test_failed_liveness_is_flagged_even_with_the_right_face(client, world, face):
    enrolled(client, world)
    done = check_in(client, world, pid=probe_id(client, world, live=FAILED))
    assert done.json()["face_result"] == "LOW_QUALITY" and done.json()["status"] == "NEEDS_REVIEW"


def test_online_liveness_needs_server_proofs_not_the_phone_claim(client, world, face):
    enrolled(client, world)
    forged = check_in(client, world, pid=probe_id(client, world, live=PASSED))             # HP mengaku lolos, tanpa bukti
    assert forged.status_code == 200
    assert forged.json()["face_result"] == "LOW_QUALITY" and forged.json()["status"] == "NEEDS_REVIEW"


def verified_flag(pid: str) -> str:
    return sync_query("SELECT liveness->>'server_verified' FROM vms.face_probe WHERE id = %s", (pid,))[0][0]


def test_challenge_proofs_are_single_use_user_bound_and_short_lived(client, world, face, monkeypatch):
    from app.core import security

    enrolled(client, world, "member", ME)
    enrolled(client, world, "leader", OTHER)
    live = proven(client, world, "member")
    first = probe_id(client, world, live=live)
    replay = probe_id(client, world, shot=3, live=live)                                    # bukti yang sama dipakai lagi
    assert (verified_flag(first), verified_flag(replay)) == ("true", "false")

    stolen = probe(client, world, "leader", OTHER, live=proven(client, world, "member"))   # bukti milik orang lain
    assert verified_flag(stolen.json()["probe_id"]) == "false"

    one_kind = proven(client, world, "member", challenges=("bawah", "bawah"))              # dua bukti, tantangan sama
    assert verified_flag(probe_id(client, world, shot=5, live=one_kind)) == "false"

    monkeypatch.setattr(security, "FACE_CHALLENGE_TTL", security.timedelta(seconds=-1))   # bukti lahir sudah kedaluwarsa
    old = probe_id(client, world, shot=6, live=proven(client, world, "member"))
    assert verified_flag(old) == "false"


def test_probe_must_belong_to_caller_and_be_fresh(client, world, face):
    enrolled(client, world, "member", ME)
    enrolled(client, world, "leader", OTHER)
    theirs = probe_id(client, world, "leader", OTHER)
    assert check_in(client, world, "member", pid=theirs).status_code == 404                # probe orang lain
    mine = probe_id(client, world)
    sync_query("UPDATE vms.face_probe SET created_at = now() - interval '30 minutes' WHERE id = %s", (mine,))
    stale = check_in(client, world, pid=mine)
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "PROBE_EXPIRED"
    assert att_count(world) == 0                                                           # tidak ada absen tersisa


def att_count(world: World, who: str = "member") -> int:
    return sync_query("SELECT count(*) FROM vms.attendance WHERE employee_id = %s", (world.employees[who],))[0][0]


def test_check_out_records_face_without_photo(client, world, face):
    enrolled(client, world)
    assert check_in(client, world, pid=probe_id(client, world, shot=1)).status_code == 200
    out = check_out(client, world, pid=probe_id(client, world, shot=2))
    assert out.status_code == 200, out.text
    assert out.json()["check_out_face_result"] == "MATCH" and out.json()["selfie_file_id"] is None
    assert sync_query("SELECT attendance_event FROM vms.face_check WHERE claimed_employee_id = %s ORDER BY checked_at",
                      (world.employees["member"],)) == [("CHECK_IN",), ("CHECK_OUT",)]


def test_check_out_with_other_face_flags_review(client, world, face):
    enrolled(client, world)
    assert check_in(client, world, pid=probe_id(client, world)).status_code == 200
    out = check_out(client, world, pid=probe_id(client, world, person=STRANGER))
    assert out.status_code == 200 and out.json()["check_out_face_result"] == "NO_MATCH"
    assert out.json()["status"] == "NEEDS_REVIEW"          # pulang tetap tercatat, hanya ditandai untuk diperiksa


def note_of(world: World, who: str = "member") -> str | None:
    return sync_query("SELECT offline_note FROM vms.attendance WHERE employee_id = %s ORDER BY check_in_at DESC LIMIT 1",
                      (world.employees[who],))[0][0]


def test_enrolled_worker_without_face_data_goes_to_review_and_client_claims_are_ignored(client, world, face):
    enrolled(client, world)
    done = check_in(client, world, face_result="MATCH", face_similarity=0.99)              # klaim HP lama, tanpa probe
    assert done.status_code == 200                                                         # tidak ditolak
    assert done.json()["face_result"] == "SKIPPED" and done.json()["status"] == "NEEDS_REVIEW"
    assert "wajah tidak diperiksa" in (note_of(world) or "")                               # alasan tampil bagi peninjau


def test_worker_without_face_enrollment_is_not_affected(client, world, face):
    assert check_in(client, world).status_code == 200                                      # belum mendaftar wajah
    assert att(world)[0] == "AUTO_VALID" and att(world)[1] is None and note_of(world) is None
    assert check_out(client, world).json()["status"] == "AUTO_VALID"


def test_withdrawn_consent_means_face_is_no_longer_expected(client, world, face):
    enrolled(client, world)
    assert consent(client, world, state="WITHDRAWN").status_code == 200
    assert check_in(client, world).status_code == 200
    assert att(world)[0] == "AUTO_VALID" and att(world)[1] is None


def test_check_out_without_face_data_goes_to_review_for_enrolled_worker(client, world, face):
    enrolled(client, world)
    assert check_in(client, world, pid=probe_id(client, world)).status_code == 200
    out = check_out(client, world)                                                         # pulang tanpa wajah
    assert out.status_code == 200 and out.json()["check_out_face_result"] == "SKIPPED"
    assert out.json()["status"] == "NEEDS_REVIEW" and "wajah tidak diperiksa" in (note_of(world) or "")


def test_offline_attendance_without_face_block_is_flagged_for_enrolled_worker(client, world, face):
    enrolled(client, world)
    phone = Phone(client, world, "member")
    phone.go_online()
    got = phone.send(phone.record("CHECK_IN"))                                             # luring TANPA blok wajah
    assert got.status_code == 200, got.text
    assert att(world)[0] == "NEEDS_REVIEW" and att(world)[1] == "SKIPPED"
    assert "wajah tidak diperiksa" in (note_of(world) or "")

    # Catatan jam & catatan wajah digabung, bukan saling menimpa.
    other = Phone(client, world, "leader")
    enrolled(client, world, "leader", OTHER)
    other.go_online()
    shifted = other.send(other.record("CHECK_IN", mocked=True))
    assert shifted.status_code == 200, shifted.text
    merged = note_of(world, "leader") or ""
    assert "wajah tidak diperiksa" in merged and "lokasi palsu" in merged


def test_offline_check_out_without_face_block_is_flagged_for_enrolled_worker(client, world, face):
    enrolled(client, world)
    phone = Phone(client, world, "member")
    phone.go_online()
    image = png(ME, 7)
    pid = probe_id_for(client, world, image)
    assert phone.send(phone.record("CHECK_IN", extra=face_block(image)), face_probe_id=pid).status_code == 200
    out = phone.send(phone.record("CHECK_OUT", after_ms=60_000))                           # pulang luring tanpa wajah
    assert out.status_code == 200, out.text
    assert att(world)[3] == "SKIPPED" and "wajah tidak diperiksa" in (note_of(world) or "")


def test_face_service_down_keeps_attendance_working_then_reverifies(client, world, face):
    enrolled(client, world)
    live = proven(client, world)          # bukti diambil saat layanan hidup (berlaku 5 menit)
    face.down = True
    made = probe(client, world, shot=5, live=live)
    assert made.status_code == 200 and made.json()["pending"] is True                      # disimpan, dihitung nanti
    pid = made.json()["probe_id"]
    done = check_in(client, world, pid=pid)
    assert done.status_code == 200 and done.json()["face_result"] == "SKIPPED"
    assert att(world)[0] == "AUTO_VALID"

    admin = world.headers(client, "admin")
    still_down = client.post("/cron/attendance/reverify-faces", headers=admin)
    assert still_down.status_code == 200 and still_down.json()["done"] == 0                # layanan masih mati

    face.down = False
    ran = client.post("/cron/attendance/reverify-faces", headers=admin)
    assert ran.status_code == 200 and ran.json()["done"] == 1
    assert att(world)[1] == "MATCH"
    assert sync_query("SELECT attendance_id IS NOT NULL FROM vms.face_check WHERE claimed_employee_id = %s",
                      (world.employees["member"],)) == [(True,)]


# ── absen luring ber-wajah ──────────────────────────────────────────────────
def face_block(image: bytes, local: str = "MATCH") -> dict:
    return {"face": {"probe_sha256": hashlib.sha256(image).hexdigest(), "local_result": local, "local_similarity": 0.8,
                     "challenges": ["bawah", "kiri"], "passed": True, "template_version": "t1"}}


def test_offline_check_in_and_out_with_face_are_recomputed_by_the_server(client, world, face):
    enrolled(client, world)
    phone = Phone(client, world, "member")
    phone.go_online()

    image_in = png(ME, 7)
    pid = probe_id_for(client, world, image_in)
    got = phone.send(phone.record("CHECK_IN", extra=face_block(image_in)), face_probe_id=pid)
    assert got.status_code == 200, got.text
    assert att(world)[1] == "MATCH"

    image_out = png(ME, 8)
    pid_out = probe_id_for(client, world, image_out)
    out = phone.send(phone.record("CHECK_OUT", after_ms=60_000, extra=face_block(image_out)), face_probe_id=pid_out)
    assert out.status_code == 200, out.text
    assert att(world)[3] == "MATCH"


def probe_id_for(client, world: World, image: bytes, who: str = "member") -> str:
    """Probe untuk absen LURING: tidak ada server saat HP merekam, jadi liveness = klaim HP (PASSED)."""
    made = probe(client, world, who, data=image, live=PASSED)
    assert made.status_code == 200, made.text
    return made.json()["probe_id"]


def test_offline_face_block_is_bound_to_the_signed_payload(client, world, face):
    enrolled(client, world)
    phone = Phone(client, world, "member")
    phone.go_online()
    image = png(ME, 7)
    pid = probe_id_for(client, world, image)

    missing = phone.send(phone.record("CHECK_IN", extra=face_block(image)))                  # probe belum diunggah
    assert missing.status_code == 422 and missing.json()["error"]["code"] == "OFFLINE_FACE_MISSING"

    swapped = phone.send(phone.record("CHECK_IN", extra=face_block(png(ME, 99))), face_probe_id=pid)   # hash beda
    assert swapped.status_code == 422 and swapped.json()["error"]["code"] == "OFFLINE_TAMPERED"
    assert att_count(world) == 0


def test_offline_local_match_but_server_no_match_is_flagged_as_possible_tampering(client, world, face):
    enrolled(client, world)
    phone = Phone(client, world, "member")
    phone.go_online()
    image = png(STRANGER, 7)                      # wajah orang lain, tetapi HP mengaku "MATCH"
    pid = probe_id_for(client, world, image)
    got = phone.send(phone.record("CHECK_IN", extra=face_block(image, local="MATCH")), face_probe_id=pid)
    assert got.status_code == 200, got.text
    assert any("kemungkinan manipulasi" in n for n in got.json()["notes"])
    assert att(world)[0] == "NEEDS_REVIEW" and att(world)[1] == "NO_MATCH"


# ── RLS: pencocokan di bawah role aplikasi ──────────────────────────────────
def test_matching_works_under_rls_as_the_app_role(client, world, face):
    enrolled(client, world, "member", ME)
    enrolled(client, world, "leader", OTHER)
    member, leader = world.employees["member"], world.employees["leader"]
    member_user = sync_query("SELECT id FROM vms.app_user WHERE login = %s", (world.logins["member"],))[0][0]

    conn = _sync_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT set_config('app.user_id', %s, true), set_config('app.organization_id', %s, true)",
                    (str(member_user), world.org_id))
        cur.execute("SET LOCAL ROLE vms_app")

        # RLS aktif: pengguna biasa hanya melihat template miliknya (3 dari 6 baris).
        cur.execute("SELECT count(*) FROM vms.face_enrollment")
        assert cur.fetchone()[0] == 3

        # Wajah OTHER murni diklaim sebagai ME: jelas tidak cocok.
        cur.execute("SELECT result::text, note FROM vms.verify_face_for_attendance("
                    "%s::uuid, %s::uuid, %s::vector, 1.0, NULL, 'uji', 'CHECK_IN')",
                    (world.org_id, member, vector_literal(vec(OTHER, 5))))
        result, note = cur.fetchone()
        assert result == "NO_MATCH" and "tidak cocok" in note

        # Cukup mirip ME (lolos ambang) tetapi LEBIH dekat ke OTHER: hanya terdeteksi bila fungsi melihat pendaftaran
        # OTHER — RLS menyembunyikannya dari pengguna biasa, jadi ini membuktikan definer bekerja.
        mixed = [0.75 * a + 0.66 * b for a, b in zip(vec(OTHER, 5), vec(ME, 5), strict=True)]
        norm = sum(x * x for x in mixed) ** 0.5
        cur.execute("SELECT result::text, note FROM vms.verify_face_for_attendance("
                    "%s::uuid, %s::uuid, %s::vector, 1.0, NULL, 'uji', 'CHECK_IN')",
                    (world.org_id, member, vector_literal([x / norm for x in mixed])))
        result, note = cur.fetchone()
        assert result == "NO_MATCH" and "lebih menyerupai karyawan lain" in note

        cur.execute("SELECT result::text FROM vms.verify_face_for_attendance("
                    "%s::uuid, %s::uuid, %s::vector, 1.0, NULL, 'uji', 'CHECK_IN')",
                    (world.org_id, member, vector_literal(vec(ME, 5))))
        assert cur.fetchone()[0] == "MATCH"

        # Pengguna biasa tidak boleh mencocokkan atas nama orang lain.
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("SELECT * FROM vms.verify_face_for_attendance(%s::uuid, %s::uuid, %s::vector, 1.0, NULL, "
                        "'uji', 'CHECK_IN')", (world.org_id, leader, vector_literal(vec(OTHER, 5))))
    finally:
        conn.rollback()
        conn.close()


# ── retensi ───────────────────────────────────────────────────────────────
def test_purge_removes_expired_probe_images_rows_and_references(client, world, face):
    enrolled(client, world)
    pid = probe_id(client, world)
    assert check_in(client, world, pid=pid).status_code == 200
    file_id, key = sync_query("SELECT fo.id, fo.storage_key FROM vms.face_probe fp JOIN vms.file_object fo "
                              "ON fo.id = fp.file_id WHERE fp.id = %s", (pid,))[0]
    assert key in face.stored

    sync_query("UPDATE vms.organization SET face_probe_retention_days = 1 WHERE id = %s", (world.org_id,))
    admin = world.headers(client, "admin")
    assert client.post("/cron/attendance/purge-face-probes", headers=admin).json()["purged"] == 0   # belum lewat

    sync_query("UPDATE vms.face_probe SET created_at = now() - interval '3 days' WHERE id = %s", (pid,))
    sync_query("UPDATE vms.face_check SET checked_at = now() - interval '3 days' WHERE claimed_employee_id = %s",
               (world.employees["member"],))
    purged = client.post("/cron/attendance/purge-face-probes", headers=admin)
    assert purged.status_code == 200 and purged.json()["purged"] >= 1

    assert key not in face.stored                                                          # objek penyimpanan hilang
    assert sync_query("SELECT count(*) FROM vms.face_probe WHERE id = %s", (pid,))[0][0] == 0
    assert sync_query("SELECT count(*) FROM vms.file_object WHERE id = %s", (file_id,))[0][0] == 0
    assert sync_query("SELECT probe_embedding IS NULL, probe_file_id IS NULL FROM vms.face_check "
                      "WHERE claimed_employee_id = %s", (world.employees["member"],)) == [(True, True)]
    assert att(world)[1] == "MATCH"                                                        # hasil absen tetap
