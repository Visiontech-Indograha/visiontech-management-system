"""
R-19 · P6-4 — laporan akhir sebagai dokumen bertanda tangan ber-QR (UAT docs/07 §6 langkah 10:
"PDF laporan akhir dicetak; QR-nya dipindai orang lain").
- Saat penyelesaian disetujui: snapshot kanonik laporan akhir + SHA-256 disimpan, ketua (penerbit) dan
  pemeriksa (APPROVER) menandatangani.
- Laporan akhir yang disetujui terkunci (dokumen terbit tidak pernah berubah).
- QR → VALID; isi dipalsukan → DOCUMENT_CHANGED.
- GET /work-plans/{id}/completion/signatures · GET /work-plans/{id}/completion/pdf (penjaga VIEW).
"""
from __future__ import annotations

from urllib.parse import quote

import psycopg2
import pytest

import app.modules.work_plans.controllers.work_plan_transitions_controller as transitions_api
from tests.conftest import World, requires_db, sync_query
from tests.modules.reports.test_weekly_reports import _approve_days
from tests.modules.work_plans.test_flow_plans import _row_version, run_plan_to_in_progress

pytestmark = requires_db

FINAL = {"body": "28 kamera terpasang dan diuji", "obstacle": "Hujan dua hari"}


def _complete(client, world: World) -> str:
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    _approve_days(day_ids)
    def post(action: str, who: str, **b):
        return client.post(f"/work-plans/{plan_id}/{action}", headers=world.headers(client, who),
                           json={"row_version": _row_version(plan_id), **b})
    assert post("request-completion", "leader", **FINAL).status_code == 200
    approved = post("approve-completion", "pm", reason="Rapi")
    assert approved.status_code == 200, approved.text
    return plan_id


def _token(world: World, signature_id: str) -> str:
    return sync_query(
        "SELECT raw_token FROM vms.issue_qr_token(%s, 'DOCUMENT_VERIFY', 'document_signature', %s, "
        "(SELECT id FROM vms.app_user WHERE employee_id = %s))",
        (world.org_id, signature_id, world.employees["pm"]))[0][0]


def test_approval_signs_the_final_report_snapshot(client, world: World):
    plan_id = _complete(client, world)

    sigs = client.get(f"/work-plans/{plan_id}/completion/signatures", headers=world.headers(client, "member"))
    assert sigs.status_code == 200, sigs.text
    rows = sigs.json()
    assert [(r["signer_role"], r["signer_name"]) for r in rows] == [
        ("ISSUER", "Karyawan uji leader"), ("APPROVER", "Karyawan uji pm")]

    snap_hash, body = sync_query("SELECT encode(snapshot_sha256, 'hex'), snapshot -> 'report' ->> 'body' "
                                 "FROM vms.final_report WHERE work_plan_id = %s", (plan_id,))[0]
    assert body == FINAL["body"]
    assert all(r["document_sha256_hex"] == snap_hash for r in rows)

    verified = client.get(f"/verify/{quote(_token(world, rows[0]['id']), safe='')}").json()
    assert verified["state"] == "VALID"
    assert verified["document_title"].startswith("Laporan akhir")


def test_approved_final_report_is_locked_and_tampering_is_detected(client, world: World):
    plan_id = _complete(client, world)
    with pytest.raises(psycopg2.Error, match="tidak dapat diubah"):
        sync_query("UPDATE vms.final_report SET body = 'diubah' WHERE work_plan_id = %s", (plan_id,))

    sig_id = client.get(f"/work-plans/{plan_id}/completion/signatures",
                        headers=world.headers(client, "pm")).json()[0]["id"]
    sync_query("SET session_replication_role = replica; "
               "UPDATE vms.final_report SET snapshot_sha256 = digest('palsu', 'sha256') WHERE work_plan_id = %s; "
               "SET session_replication_role = origin;", (plan_id,))
    tampered = client.get(f"/verify/{quote(_token(world, sig_id), safe='')}").json()
    assert tampered["state"] == "DOCUMENT_CHANGED"


def test_final_report_pdf_has_a_qr_per_signature(client, world: World, other_world, monkeypatch):
    plan_id = _complete(client, world)
    rendered: dict[str, str] = {}

    def fake_pdf(html: str) -> bytes:        # WeasyPrint butuh Pango (ada di image Linux, tidak di Windows dev)
        rendered["html"] = html
        return b"%PDF-1.7 uji"

    monkeypatch.setattr(transitions_api, "html_to_pdf", fake_pdf)
    pdf = client.get(f"/work-plans/{plan_id}/completion/pdf", headers=world.headers(client, "leader"))
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    html = rendered["html"]
    assert html.count('alt="QR verifikasi') == 2
    assert FINAL["body"] in html and FINAL["obstacle"] in html
    assert "Karyawan uji leader" in html and "Karyawan uji pm" in html

    assert client.get(f"/work-plans/{plan_id}/completion/pdf",
                      headers=other_world.headers(client, "pm")).status_code == 404


def test_pdf_is_only_for_approved_final_reports(client, world: World):
    plan_id, _ = run_plan_to_in_progress(client, world)
    response = client.get(f"/work-plans/{plan_id}/completion/pdf", headers=world.headers(client, "pm"))
    assert response.status_code == 409
