"""
R-34 · Absen lapangan luring (keputusan pemilik 2026-10-02 — mengubah K-13), alur disetujui setelah uji nyata
di HP & web. HP merekam absen tanpa sinyal, menandatanganinya dengan kunci Android Keystore, lalu mengirimnya
otomatis saat online. Uji ini memerankan HP: kunci EC P-256, payload JSON bertanda tangan, jangkar jam server.

Yang dijaga:
- data yang diubah setelah direkam (lokasi/jam/swafoto) ditolak `OFFLINE_TAMPERED`;
- jam absen = jangkar server + penghitung waktu internal, BUKAN jam HP;
- valid otomatis hanya bila semua cek lolos; selain itu Perlu review dengan catatan server;
- absen pulang luring: masuk valid → langsung tercatat; Perlu review → ditahan, berlaku saat disetujui,
  gugur saat ditolak;
- kirim ulang tidak menggandakan (idempoten per `client_op_id`).
"""
from __future__ import annotations

import base64
import io
import json
import time
import uuid
from datetime import timedelta

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from PIL import Image

from app.core import security
from app.core.time import utcnow
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

INSIDE = (-6.2, 106.8)     # tepat di lokasi uji (radius 100 m)
OUTSIDE = (-6.3, 106.8)    # ±11 km
ANCHOR_ELAPSED = 5_000_000  # penghitung waktu internal HP saat jangkar disimpan (ms sejak HP menyala)


class Phone:
    """HP lapangan tiruan: kunci Keystore, jangkar jam dari server, dan absen luring bertanda tangan."""

    def __init__(self, client, world: World, who: str = "member"):
        self.client, self.world, self.who = client, world, who
        self.headers = world.headers(client, who)
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.device_id = "hp-uji-" + uuid.uuid4().hex[:10]
        self.anchor: str | None = None

    def public_key(self) -> str:
        der = self.key.public_key().public_bytes(serialization.Encoding.DER,
                                                 serialization.PublicFormat.SubjectPublicKeyInfo)
        return base64.b64encode(der).decode()

    def go_online(self) -> None:
        """Buka Absensi saat online: simpan jangkar jam & daftarkan kunci (seperti `_load` di HP)."""
        listed = self.client.get("/attendance", headers=self.headers)
        assert listed.status_code == 200, listed.text
        self.anchor = listed.json()["time_anchor"]
        assert self.anchor
        registered = self.client.post("/attendance/device-key", headers=self.headers,
                                      json={"device_id": self.device_id, "public_key": self.public_key()})
        assert registered.status_code == 200, registered.text

    def record(self, kind: str, *, at=INSIDE, after_ms: int = 2_000, boot: tuple[int, int] = (7, 7),
               gps_shift_ms: int = 0, mocked: bool = False, explanation: str | None = None,
               selfie_sha: str | None = None, anchor: str | None = None) -> dict:
        """Absen luring yang direkam `after_ms` setelah jangkar. Jam HP sengaja dimajukan 3 jam."""
        anchor_token = anchor if anchor is not None else self.anchor
        anchor_ms = security.verify_time_anchor(anchor_token or "", self._user_id()) or int(time.time() * 1000)
        op = str(uuid.uuid4())
        payload = json.dumps({
            "client_op_id": op, "kind": kind, "device_id": self.device_id, "site_id": self.world.site_id,
            "site_name": "Gudang uji", "lat": at[0], "lng": at[1], "accuracy_m": 8.0, "mocked": mocked,
            "anchor_token": anchor_token, "anchor_elapsed_ms": ANCHOR_ELAPSED, "anchor_boot_count": boot[0],
            "event_elapsed_ms": ANCHOR_ELAPSED + after_ms, "event_boot_count": boot[1],
            "gps_time_ms": anchor_ms + after_ms + gps_shift_ms,
            "device_time_ms": anchor_ms + after_ms + 3 * 3600 * 1000,
            "explanation": explanation, "selfie_sha256": selfie_sha,
        }, separators=(",", ":"))
        signature = base64.b64encode(self.key.sign(payload.encode(), ec.ECDSA(hashes.SHA256()))).decode()
        return {"device_id": self.device_id, "client_op_id": op, "kind": kind, "payload": payload,
                "signature": signature}

    def send(self, event: dict, selfie_file_id: str | None = None):
        body = {**event, **({"selfie_file_id": selfie_file_id} if selfie_file_id else {})}
        return self.client.post("/attendance/offline", headers=self.headers, json=body)

    def _user_id(self) -> str:
        return str(sync_query("SELECT id FROM vms.app_user WHERE login = %s", (self.world.logins[self.who],))[0][0])


def _selfie(client, world: World, who: str = "member") -> tuple[str, str]:
    """Unggah swafoto → (file_id, sha256 hex yang disimpan server)."""
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (uuid.uuid4().int % 255, 90, 30)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("swafoto.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    file_id = uploaded.json()["file_id"]
    sha = sync_query("SELECT encode(sha256, 'hex') FROM vms.file_object WHERE id = %s", (file_id,))[0][0]
    return file_id, sha


def _row(att_id: str) -> tuple:
    return sync_query(
        "SELECT status::text, offline, offline_note, check_in_at, check_out_at, check_out_requested_at, explanation "
        "FROM vms.attendance WHERE id = %s", (att_id,))[0]


def _count(world: World, who: str = "member") -> int:
    return sync_query("SELECT count(*) FROM vms.attendance WHERE employee_id = %s",
                      (world.employees[who],))[0][0]


def _review(client, world: World, att_id: str, approve: bool):
    return client.post(f"/attendance/{att_id}/review", headers=world.headers(client, "pm"),
                       json={"is_approved": approve, "note": "Diperiksa PM unit"})


# ── Pendaftaran kunci perangkat ───────────────────────────────────────────────────────────────
def test_device_key_must_be_an_ec_p256_public_key(client, world):
    phone = Phone(client, world)
    rsa_like = base64.b64encode(b"bukan kunci" * 8).decode()
    bad = client.post("/attendance/device-key", headers=phone.headers,
                      json={"device_id": phone.device_id, "public_key": rsa_like})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "DEVICE_KEY_INVALID"


def test_offline_event_from_unregistered_device_is_refused(client, world):
    phone = Phone(client, world)
    phone.anchor = client.get("/attendance", headers=phone.headers).json()["time_anchor"]
    refused = phone.send(phone.record("CHECK_IN"))
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "DEVICE_KEY_MISSING"
    assert _count(world) == 0


# ── Absen masuk luring ────────────────────────────────────────────────────────────────────────
def test_genuine_offline_check_in_is_auto_valid_and_uses_anchor_time_not_phone_clock(client, world):
    phone = Phone(client, world)
    phone.go_online()
    event = phone.record("CHECK_IN", after_ms=90_000)
    accepted = phone.send(event)
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["result"] == "AUTO_VALID" and body["time_trusted"] is True and body["notes"] == []
    status, offline, note, check_in_at, *_ = _row(body["attendance_id"])
    assert (status, offline, note) == ("AUTO_VALID", True, None)
    # jam = jangkar + 90 detik penghitung internal; jam HP (+3 jam) diabaikan
    expected_ms = json.loads(event["payload"])["gps_time_ms"]
    assert abs(check_in_at.timestamp() * 1000 - expected_ms) < 1_000
    assert abs(check_in_at - utcnow()) < timedelta(minutes=5)


def test_offline_event_changed_after_recording_is_rejected_as_tampered(client, world):
    phone = Phone(client, world)
    phone.go_online()
    event = phone.record("CHECK_IN", at=OUTSIDE, explanation="Jalan ditutup")
    # Pengguna mengedit data aplikasi: titik dipindah ke dalam zona — tanda tangan tidak lagi cocok.
    event["payload"] = event["payload"].replace('"lat":-6.3', '"lat":-6.2')
    rejected = phone.send(event)
    assert rejected.status_code == 422 and rejected.json()["error"]["code"] == "OFFLINE_TAMPERED"
    assert "diubah setelah direkam" in rejected.json()["error"]["message"]
    assert _count(world) == 0


def test_offline_event_signed_by_another_phone_is_rejected(client, world):
    phone = Phone(client, world)
    phone.go_online()
    event = phone.record("CHECK_IN")
    impostor = ec.generate_private_key(ec.SECP256R1())
    event["signature"] = base64.b64encode(impostor.sign(event["payload"].encode(), ec.ECDSA(hashes.SHA256()))).decode()
    rejected = phone.send(event)
    assert rejected.status_code == 422 and rejected.json()["error"]["code"] == "OFFLINE_TAMPERED"


def test_resending_the_same_offline_event_does_not_duplicate(client, world):
    phone = Phone(client, world)
    phone.go_online()
    event = phone.record("CHECK_IN")
    first = phone.send(event)
    again = phone.send(event)
    assert first.status_code == again.status_code == 200
    assert again.json()["duplicate"] is True and again.json()["attendance_id"] == first.json()["attendance_id"]
    assert _count(world) == 1


def test_offline_outside_zone_needs_explanation_and_the_recorded_selfie(client, world, fake_storage):
    phone = Phone(client, world)
    phone.go_online()
    no_reason = phone.send(phone.record("CHECK_IN", at=OUTSIDE))
    assert no_reason.status_code == 422 and no_reason.json()["error"]["code"] == "EXPLANATION_REQUIRED"

    file_id, sha = _selfie(client, world)
    other_file, _ = _selfie(client, world)
    swapped = phone.send(phone.record("CHECK_IN", at=OUTSIDE, explanation="Jalan ditutup", selfie_sha=sha),
                         selfie_file_id=other_file)
    assert swapped.status_code == 422 and swapped.json()["error"]["code"] == "OFFLINE_TAMPERED"

    accepted = phone.send(phone.record("CHECK_IN", at=OUTSIDE, explanation="Jalan ditutup", selfie_sha=sha),
                          selfie_file_id=file_id)
    assert accepted.status_code == 200, accepted.text
    status, offline, _, _, _, _, explanation = _row(accepted.json()["attendance_id"])
    assert (status, offline, explanation) == ("NEEDS_REVIEW", True, "Jalan ditutup")


def test_phone_restarted_while_offline_uses_gps_time_and_needs_review(client, world):
    phone = Phone(client, world)
    phone.go_online()
    accepted = phone.send(phone.record("CHECK_IN", boot=(7, 8)))
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["result"] == "NEEDS_REVIEW" and body["time_trusted"] is False
    assert _row(body["attendance_id"])[2] == "jam hanya dari satelit GPS (HP dinyalakan ulang saat luring)"


def test_clock_not_matching_gps_or_mock_location_needs_review(client, world, other_world):
    phone = Phone(client, world)
    phone.go_online()
    drift = phone.send(phone.record("CHECK_IN", gps_shift_ms=10 * 60_000))
    assert drift.status_code == 200 and drift.json()["result"] == "NEEDS_REVIEW"
    assert _row(drift.json()["attendance_id"])[2] == "jam tidak cocok dengan waktu satelit GPS"

    other = Phone(client, other_world)
    other.go_online()
    mocked = other.send(other.record("CHECK_IN", mocked=True))
    assert mocked.status_code == 200 and mocked.json()["result"] == "NEEDS_REVIEW"
    assert _row(mocked.json()["attendance_id"])[2] == "lokasi palsu terdeteksi"


def test_sent_more_than_24_hours_later_needs_review_and_after_7_days_is_refused(client, world, monkeypatch):
    phone = Phone(client, world)
    phone.go_online()
    user_id = phone._user_id()
    real_now = utcnow()
    monkeypatch.setattr(security, "utcnow", lambda: real_now - timedelta(hours=25))
    old_anchor = security.create_time_anchor(user_id)
    monkeypatch.setattr(security, "utcnow", lambda: real_now - timedelta(days=8))
    ancient_anchor = security.create_time_anchor(user_id)
    monkeypatch.undo()

    late = phone.send(phone.record("CHECK_IN", anchor=old_anchor))
    assert late.status_code == 200, late.text
    assert late.json()["result"] == "NEEDS_REVIEW" and late.json()["time_trusted"] is True
    assert _row(late.json()["attendance_id"])[2] == "terkirim lebih dari 24 jam setelah absen"

    too_old = phone.send(phone.record("CHECK_IN", anchor=ancient_anchor))
    assert too_old.status_code == 422 and too_old.json()["error"]["code"] == "OFFLINE_TOO_OLD"


def test_office_account_cannot_send_offline_attendance(client, world):
    sync_query("UPDATE vms.employee SET attendance_mode = 'OFFICE' WHERE id = %s RETURNING id",
               (world.employees["leader"],))
    phone = Phone(client, world, "leader")
    phone.go_online()
    refused = phone.send(phone.record("CHECK_IN"))
    assert refused.status_code == 403 and refused.json()["error"]["code"] == "WRONG_ATTENDANCE_CHANNEL"
    refused_out = phone.send(phone.record("CHECK_OUT"))
    assert refused_out.status_code == 403 and refused_out.json()["error"]["code"] == "WRONG_ATTENDANCE_CHANNEL"


# ── Absen pulang luring ───────────────────────────────────────────────────────────────────────
def test_offline_check_out_after_valid_check_in_is_recorded_at_its_own_time(client, world):
    phone = Phone(client, world)
    phone.go_online()
    att_id = phone.send(phone.record("CHECK_IN", after_ms=1_000)).json()["attendance_id"]
    out_event = phone.record("CHECK_OUT", after_ms=60_000)
    closed = phone.send(out_event)
    assert closed.status_code == 200, closed.text
    assert closed.json()["result"] == "CHECKED_OUT" and closed.json()["attendance_id"] == att_id
    check_out_at = _row(att_id)[4]
    assert abs(check_out_at.timestamp() * 1000 - json.loads(out_event["payload"])["gps_time_ms"]) < 1_000


def test_offline_check_out_without_check_in_is_refused(client, world):
    phone = Phone(client, world)
    phone.go_online()
    refused = phone.send(phone.record("CHECK_OUT"))
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "NO_OPEN_SESSION"


def test_check_out_on_review_is_held_then_applied_when_approved(client, world, fake_storage):
    phone = Phone(client, world)
    phone.go_online()
    file_id, sha = _selfie(client, world)
    att_id = phone.send(phone.record("CHECK_IN", at=OUTSIDE, explanation="Posko luar", selfie_sha=sha),
                        selfie_file_id=file_id).json()["attendance_id"]
    held = phone.send(phone.record("CHECK_OUT", after_ms=120_000))
    assert held.status_code == 200 and held.json()["result"] == "CHECK_OUT_PENDING_REVIEW"
    _, _, _, _, check_out_at, requested_at, _ = _row(att_id)
    assert check_out_at is None and requested_at is not None

    # Peninjau melihat tanda luring & jam pulang yang ditahan di daftar absensi.
    listed = client.get("/attendance", headers=world.headers(client, "pm")).json()["items"]
    item = next(i for i in listed if i["id"] == att_id)
    assert item["offline"] is True and item["check_out_requested_at"] is not None and item["can_review"] is True

    assert _review(client, world, att_id, approve=True).status_code == 200
    status, _, _, _, check_out_at, requested_at, _ = _row(att_id)
    assert status == "APPROVED" and check_out_at == requested_at


def test_held_check_out_is_dropped_when_the_check_in_is_rejected(client, world, fake_storage):
    phone = Phone(client, world)
    phone.go_online()
    file_id, sha = _selfie(client, world)
    att_id = phone.send(phone.record("CHECK_IN", at=OUTSIDE, explanation="Posko luar", selfie_sha=sha),
                        selfie_file_id=file_id).json()["attendance_id"]
    phone.send(phone.record("CHECK_OUT", after_ms=120_000))
    assert _review(client, world, att_id, approve=False).status_code == 200
    status, _, _, _, check_out_at, _, _ = _row(att_id)
    assert status == "REJECTED" and check_out_at is None
