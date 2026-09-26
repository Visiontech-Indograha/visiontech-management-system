"""
Fase 6 · Tanda tangan dokumen ber-QR (dok 02 A-09/A-13, dok 05 §3.9, db/04).
Keputusan pemilik 2026-09-26: otomatis — penerbit (PM) saat terbit = ISSUER, ketua saat menerima = ACCEPTOR;
kunci lokal dulu (KMS sebelum produksi).
- GET /work-plans/{id}/documents · GET /documents/{id}/signatures · GET /documents/{id}/pdf
- POST /signatures/{id}/revoke {reason} (PM unit/OPS) · GET /verify/{token} PUBLIK, 30/menit per IP
"""
from __future__ import annotations

from urllib.parse import quote

import app.api.signatures as signatures_api
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import run_plan_to_accepted

pytestmark = requires_db


def _document(client, world: World, plan_id: str) -> dict:
    docs = client.get(f"/work-plans/{plan_id}/documents", headers=world.headers(client, "member"))
    assert docs.status_code == 200, docs.text
    assert len(docs.json()) == 1
    return docs.json()[0]


def _token(world: World, signature_id: str) -> str:
    """Token QR mentah hanya ada di QR — di uji diterbitkan langsung lewat fungsi DB yang sama."""
    return sync_query(
        "SELECT raw_token FROM vms.issue_qr_token(%s, 'DOCUMENT_VERIFY', 'document_signature', %s, "
        "(SELECT id FROM vms.app_user WHERE employee_id = %s))",
        (world.org_id, signature_id, world.employees["pm"]))[0][0]


def _verify(client, token: str):
    return client.get(f"/verify/{quote(token, safe='')}")


def test_publish_and_accept_sign_the_document(client, world: World):
    plan_id, _ = run_plan_to_accepted(client, world)

    document = _document(client, world, plan_id)
    assert document["signature_count"] == 2
    signatures = client.get(f"/documents/{document['id']}/signatures", headers=world.headers(client, "member"))
    assert signatures.status_code == 200, signatures.text
    rows = signatures.json()
    assert [r["signer_role"] for r in rows] == ["ISSUER", "ACCEPTOR"]
    assert [r["signer_name"] for r in rows] == ["Karyawan uji pm", "Karyawan uji leader"]
    assert len({r["serial_number"] for r in rows}) == 2
    assert all(r["document_sha256_hex"] == document["sha256"] and r["signature_alg"] == "Ed25519" for r in rows)
    assert sync_query("SELECT count(*) FROM vms.signing_key WHERE organization_id = %s AND public_key IS NOT NULL",
                      (world.org_id,)) == [(1,)]


def test_public_verification_and_revocation(client, world: World):
    plan_id, _ = run_plan_to_accepted(client, world)
    document = _document(client, world, plan_id)
    issuer = client.get(f"/documents/{document['id']}/signatures", headers=world.headers(client, "pm")).json()[0]
    token = _token(world, issuer["id"])

    valid = _verify(client, token)                                        # tanpa login
    assert valid.status_code == 200, valid.text
    body = valid.json()
    assert (body["state"], body["serial_number"], body["signer_name"]) == \
        ("VALID", issuer["serial_number"], "Karyawan uji pm")
    assert body["document_sha256_hex"] == document["sha256"]
    assert _verify(client, "token-palsu").json()["state"] == "UNKNOWN"

    revoke = f"/signatures/{issuer['id']}/revoke"
    assert client.post(revoke, headers=world.headers(client, "member"), json={"reason": "x"}).status_code == 403
    no_reason = client.post(revoke, headers=world.headers(client, "pm"), json={"reason": " "})
    assert no_reason.status_code == 422 and no_reason.json()["error"]["message"] == "Alasan pencabutan wajib diisi."
    assert client.post(revoke, headers=world.headers(client, "pm"), json={"reason": "Salah penandatangan"}) \
        .status_code == 200
    again = client.post(revoke, headers=world.headers(client, "pm"), json={"reason": "lagi"})
    assert again.status_code == 409

    revoked = _verify(client, token).json()
    assert (revoked["state"], revoked["note"]) == ("REVOKED", "Salah penandatangan")


def test_other_organisation_cannot_see_documents(client, world: World, other_world: World):
    plan_id, _ = run_plan_to_accepted(client, world)
    document = _document(client, world, plan_id)

    assert client.get(f"/work-plans/{plan_id}/documents", headers=other_world.headers(client, "pm")).status_code == 404
    assert client.get(f"/documents/{document['id']}/signatures",
                      headers=other_world.headers(client, "pm")).status_code == 404


def test_pdf_shows_qr_for_each_valid_signature(client, world: World, monkeypatch):
    plan_id, _ = run_plan_to_accepted(client, world)
    document = _document(client, world, plan_id)
    rendered: dict[str, str] = {}

    def fake_pdf(html: str) -> bytes:        # WeasyPrint butuh Pango (ada di image Linux, tidak di Windows dev)
        rendered["html"] = html
        return b"%PDF-1.7 uji"

    monkeypatch.setattr(signatures_api, "html_to_pdf", fake_pdf)
    pdf = client.get(f"/documents/{document['id']}/pdf", headers=world.headers(client, "leader"))

    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    html = rendered["html"]
    assert html.count('alt="QR verifikasi') == 2  # satu QR per tanda tangan berlaku
    assert html.count("data:image/png;base64,") == 3  # 2 QR + logo kop
    assert "Karyawan uji pm" in html and "Karyawan uji leader" in html and document["sha256"] in html


def test_public_verification_is_rate_limited(client, world: World, monkeypatch):
    monkeypatch.setattr(signatures_api, "VERIFY_LIMIT", 3)
    signatures_api._verify_hits.clear()

    codes = [_verify(client, "token-palsu").status_code for _ in range(4)]

    assert codes == [200, 200, 200, 429]
    signatures_api._verify_hits.clear()


# ── dok 07 §4.2 · pemalsuan isi & rotasi kunci ─────────────────────────────────────────────────
def _signatures(client, world: World, document_id: str) -> list[dict]:
    rows = client.get(f"/documents/{document_id}/signatures", headers=world.headers(client, "pm"))
    assert rows.status_code == 200, rows.text
    return rows.json()


def test_tampered_document_is_reported_as_changed(client, world: World):
    """Satu byte isi dokumen diubah langsung di basis data (melewati trigger kekekalan R4) →
    verifikasi publik menyatakan DOCUMENT_CHANGED, bukan VALID."""
    plan_id, _ = run_plan_to_accepted(client, world)
    document = _document(client, world, plan_id)
    token = _token(world, _signatures(client, world, document["id"])[0]["id"])
    assert _verify(client, token).json()["state"] == "VALID"

    sync_query("SET session_replication_role = replica; "
               "UPDATE vms.plan_document SET snapshot_sha256 = digest(snapshot::text || 'x', 'sha256') WHERE id = %s; "
               "SET session_replication_role = origin;", (document["id"],))

    tampered = _verify(client, token).json()
    assert tampered["state"] == "DOCUMENT_CHANGED"
    assert "berbeda" in tampered["note"]


def test_rotated_key_keeps_old_signatures_valid(client, world: World, monkeypatch):
    """Kunci dirotasi → tanda tangan baru memakai kunci baru, tanda tangan lama tetap VALID dan
    tetap terverifikasi secara kriptografis oleh kunci publik lamanya."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    from app.core import signing
    from app.core.config import settings

    def rotate(seed: str) -> None:
        monkeypatch.setattr(settings, "DOC_SIGNING_KEY_HEX", seed)
        signing.get_document_signer.cache_clear()

    rotate("0a" * 32)
    old_plan, _ = run_plan_to_accepted(client, world)
    old_doc = _document(client, world, old_plan)
    old_sig = _signatures(client, world, old_doc["id"])[0]

    rotate("0b" * 32)
    try:
        new_plan, _ = run_plan_to_accepted(client, world, start_offset_days=10)  # tim sama, periode lain
        new_sig = _signatures(client, world, _document(client, world, new_plan)["id"])[0]
    finally:
        signing.get_document_signer.cache_clear()

    keys = sync_query("SELECT s.id::text, k.kid, k.public_key, s.signature, s.signed_payload "
                      "FROM vms.document_signature s JOIN vms.signing_key k ON k.id = s.signing_key_id "
                      "WHERE s.id IN (%s, %s)", (old_sig["id"], new_sig["id"]))
    by_id = {row[0]: row for row in keys}
    assert by_id[old_sig["id"]][1] != by_id[new_sig["id"]][1]      # kid berbeda = kunci berbeda

    _, _, public_key, signature, payload = by_id[old_sig["id"]]
    Ed25519PublicKey.from_public_bytes(bytes(public_key)).verify(bytes(signature), signing.canonical(payload))
    assert _verify(client, _token(world, old_sig["id"])).json()["state"] == "VALID"
    assert _verify(client, _token(world, new_sig["id"])).json()["state"] == "VALID"
