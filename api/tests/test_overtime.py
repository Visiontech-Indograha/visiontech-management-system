"""
V-28 · REPORT_OVERTIME, REVIEW_OVERTIME + rekap lembur (domain.js baris 607–627).

Aturan yang diuji:
  - REPORT: hanya SK IN_PROGRESS; 0 < jam ≤ 12; alasan wajib; hanya ketua/anggota;
    tanggal dari server; duplikat non-REJECTED → 409.
  - REVIEW: hanya PENDING_PM; hanya PM unit / OPS; pengaju ≠ peninjau;
    keputusan APPROVED / REJECTED.
  - LIST: siapa pun yang dapat melihat SK.
  - RECAP: hanya Finance / OPS / Admin; hanya jam APPROVED yang dihitung.
  - Visibilitas lintas organisasi: SK asing → 404.
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import (
    run_plan_to_accepted,
    run_plan_to_in_progress,
)

pytestmark = requires_db


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _report(client, world: World, plan_id: str, who: str,
            hours: float = 2.0, reason: str = "Pengerjaan kabel tambahan") -> object:
    return client.post(
        "/overtime",
        headers=world.headers(client, who),
        json={"work_plan_id": plan_id, "hours": hours, "reason": reason},
    )


def _review(client, world: World, ot_id: str, who: str,
            decision: str = "APPROVED", note: str | None = None) -> object:
    return client.post(
        f"/overtime/{ot_id}/review",
        headers=world.headers(client, who),
        json={"decision": decision, "note": note},
    )


def _list(client, world: World, plan_id: str, who: str) -> object:
    return client.get("/overtime", headers=world.headers(client, who), params={"work_plan_id": plan_id})


def _recap(client, world: World, who: str, month: str | None = None) -> object:
    params = f"?month={month}" if month else ""
    return client.get(f"/recaps/overtime{params}", headers=world.headers(client, who))


def _ot_status(ot_id: str) -> str:
    return sync_query("SELECT status::text FROM vms.overtime_log WHERE id = %s", (ot_id,))[0][0]


# ---------------------------------------------------------------------------
# 1. REPORT_OVERTIME — aturan bisnis
# ---------------------------------------------------------------------------

def test_report_overtime_happy_path(client, world: World):
    """Ketua berhasil mengajukan lembur pada SK yang sedang berjalan."""
    plan_id, _ = run_plan_to_in_progress(client, world)

    resp = _report(client, world, plan_id, "leader")
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["work_plan_id"] == plan_id
    assert data["hours"] == 2.0
    assert data["status"] == "PENDING_PM"
    assert data["work_date"] is not None   # tanggal server, bukan None


def test_member_can_also_report_overtime(client, world: World):
    """domain.js baris 611: anggota juga boleh mengajukan lembur."""
    plan_id, _ = run_plan_to_in_progress(client, world)

    resp = _report(client, world, plan_id, "member")
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "PENDING_PM"


def test_report_requires_in_progress_status(client, world: World):
    """domain.js baris 608: SK yang bukan IN_PROGRESS → 409."""
    plan_id, _ = run_plan_to_accepted(client, world, start_offset_days=1)   # ACCEPTED, mulai besok (alur v2)

    resp = _report(client, world, plan_id, "leader")
    assert resp.status_code == 409
    assert resp.json()["error"]["message"] == "Hanya pekerjaan aktif yang bisa diajukan lembur."


def test_report_hours_validation(client, world: World):
    """domain.js baris 609: 0 < jam ≤ 12; jam = 0 atau > 12 → 422."""
    plan_id, _ = run_plan_to_in_progress(client, world)

    for bad_hours in (0, -1, 12.1, 13, 100):
        resp = _report(client, world, plan_id, "leader", hours=bad_hours)
        assert resp.status_code == 422, f"Diharapkan 422 untuk jam={bad_hours}"
        assert resp.json()["error"]["message"] == "Jam lembur tidak valid."

    # Batas tepat: 12.0 harus diterima
    resp = _report(client, world, plan_id, "member", hours=12.0)
    assert resp.status_code == 201, resp.text


def test_report_reason_required(client, world: World):
    """domain.js baris 610: alasan kosong/spasi → 422."""
    plan_id, _ = run_plan_to_in_progress(client, world)

    for bad_reason in ("", "   "):
        resp = _report(client, world, plan_id, "leader", reason=bad_reason)
        assert resp.status_code == 422, f"Diharapkan 422 untuk reason={bad_reason!r}"
        assert resp.json()["error"]["message"] == "Alasan lembur wajib diisi."


def test_only_team_member_can_report(client, world: World):
    """domain.js baris 611: PM tidak boleh mengajukan lembur (bukan anggota tim)."""
    plan_id, _ = run_plan_to_in_progress(client, world)

    resp = _report(client, world, plan_id, "pm")
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["message"] == "Hanya ketua atau anggota pekerjaan ini yang dapat mengajukan lembur."


def test_other_org_cannot_report(client, world: World, other_world: World):
    """SK organisasi lain → 404 (keberadaan SK tidak bocor)."""
    plan_id, _ = run_plan_to_in_progress(client, world)

    resp = _report(client, other_world, plan_id, "leader")
    assert resp.status_code == 404


def test_duplicate_overtime_same_day_rejected(client, world: World):
    """unique index overtime_no_double_uidx: pengajuan duplikat (emp, plan, date) non-REJECTED → 409."""
    plan_id, _ = run_plan_to_in_progress(client, world)

    first = _report(client, world, plan_id, "leader")
    assert first.status_code == 201

    second = _report(client, world, plan_id, "leader", hours=3.0)
    assert second.status_code == 409
    assert "sudah ada" in second.json()["error"]["message"]


# ---------------------------------------------------------------------------
# 2. REVIEW_OVERTIME — aturan bisnis
# ---------------------------------------------------------------------------

def test_review_approved(client, world: World):
    """PM berhasil menyetujui lembur PENDING_PM."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    ot_id = _report(client, world, plan_id, "leader").json()["id"]

    resp = _review(client, world, ot_id, "pm", decision="APPROVED")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "APPROVED"
    assert _ot_status(ot_id) == "APPROVED"


def test_review_rejected_with_note(client, world: World):
    """PM menolak lembur; field review_note tersimpan."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    ot_id = _report(client, world, plan_id, "leader").json()["id"]

    resp = _review(client, world, ot_id, "pm", decision="REJECTED", note="Tidak ada SPK lembur")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "REJECTED"
    assert data["review_note"] == "Tidak ada SPK lembur"


def test_ops_can_review_overtime(client, world: World):
    """domain.js: OPS punya REVIEW_OVERTIME lintas unit."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    ot_id = _report(client, world, plan_id, "leader").json()["id"]

    resp = _review(client, world, ot_id, "ops", decision="APPROVED")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "APPROVED"


def test_reviewer_cannot_be_same_as_submitter(client, world: World):
    """domain.js baris 621: pengaju tidak dapat menyetujui sendiri."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    # leader mengajukan lembur
    ot_id = _report(client, world, plan_id, "leader").json()["id"]

    # Ketua juga PM unit SK ini → ia pengelola, jadi penolakan murni karena ia pengajunya.
    sync_query("INSERT INTO vms.user_role (user_id, role, unit_id) "
               "SELECT id, 'PM', %s FROM vms.app_user WHERE employee_id = %s",
               (world.unit_id, world.employees["leader"]))
    resp = _review(client, world, ot_id, "leader", decision="APPROVED")
    assert resp.status_code == 403
    assert resp.json()["error"]["message"] == "Pengaju lembur tidak dapat menyetujui pengajuannya sendiri."
    assert _ot_status(ot_id) == "PENDING_PM"


def test_review_only_pending_pm(client, world: World):
    """domain.js baris 618: lembur yang sudah APPROVED tidak bisa direview ulang → 409."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    ot_id = _report(client, world, plan_id, "leader").json()["id"]
    _review(client, world, ot_id, "pm", decision="APPROVED")

    # Coba review lagi
    resp = _review(client, world, ot_id, "pm", decision="REJECTED")
    assert resp.status_code == 409
    assert resp.json()["error"]["message"] == "Lembur tidak tersedia untuk direview."


def test_review_invalid_decision(client, world: World):
    """Keputusan selain APPROVED/REJECTED → 422."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    ot_id = _report(client, world, plan_id, "leader").json()["id"]

    resp = _review(client, world, ot_id, "pm", decision="MAYBE")
    assert resp.status_code == 422
    assert resp.json()["error"]["message"] == "Keputusan harus disetujui atau ditolak."


def test_pm_other_unit_cannot_review(client, world: World):
    """domain.js baris 620: PM unit lain → 403."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    ot_id = _report(client, world, plan_id, "leader").json()["id"]

    # Buat unit kedua dan PM-nya
    unit2 = world.add_unit("UNIT2")
    world.add_person("pm2", "PM", unit2, per_unit=True)

    resp = _review(client, world, ot_id, "pm2", decision="APPROVED")
    assert resp.status_code == 403


def test_review_other_org_ot_returns_404(client, world: World, other_world: World):
    """Lembur organisasi lain → 404."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    ot_id = _report(client, world, plan_id, "leader").json()["id"]

    resp = _review(client, other_world, ot_id, "pm", decision="APPROVED")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 3. GET /work-plans/{id}/overtime — daftar
# ---------------------------------------------------------------------------

def test_list_overtime_by_plan(client, world: World):
    """Siapa pun yang dapat melihat SK bisa melihat daftar lemburnya."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    _report(client, world, plan_id, "leader")
    _report(client, world, plan_id, "member")

    for who in ("leader", "member", "pm", "ops"):
        resp = _list(client, world, plan_id, who)
        assert resp.status_code == 200, f"{who}: {resp.text}"
        assert len(resp.json()) == 2


def test_list_overtime_other_org_returns_404(client, world: World, other_world: World):
    """Daftar lembur SK asing → 404."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    resp = _list(client, other_world, plan_id, "pm")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. GET /overtime/recap — rekap (hanya Finance/OPS/Admin)
# ---------------------------------------------------------------------------

def test_recap_only_approved_hours(client, world: World):
    """Rekap hanya menghitung jam APPROVED; PENDING_PM dan REJECTED tidak masuk."""
    plan_id, _ = run_plan_to_in_progress(client, world)

    # leader: 3 jam → APPROVED
    ot1_id = _report(client, world, plan_id, "leader", hours=3.0).json()["id"]
    _review(client, world, ot1_id, "pm", decision="APPROVED")

    # member: 2 jam → REJECTED
    ot2_id = _report(client, world, plan_id, "member", hours=2.0).json()["id"]
    _review(client, world, ot2_id, "pm", decision="REJECTED")

    resp = _recap(client, world, "finance")
    assert resp.status_code == 200, resp.text
    rows = resp.json()

    # Hanya leader yang punya approved_hours = 3
    approved = [r for r in rows if r["approved_hours"] > 0]
    assert len(approved) == 1
    assert approved[0]["approved_hours"] == 3.0
    assert approved[0]["approved_entries"] == 1


def test_recap_filter_by_month(client, world: World):
    """Filter ?month=YYYY-MM hanya mengembalikan data bulan itu."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    ot_id = _report(client, world, plan_id, "leader", hours=1.0).json()["id"]
    _review(client, world, ot_id, "pm", decision="APPROVED")

    # Cari bulan dari work_date yang tersimpan
    row = sync_query("SELECT work_date FROM vms.overtime_log WHERE id = %s", (ot_id,))[0]
    month_str = row[0].strftime("%Y-%m")

    resp_filtered = _recap(client, world, "finance", month=month_str)
    assert resp_filtered.status_code == 200
    assert len(resp_filtered.json()) >= 1

    # Bulan yang tidak ada datanya harus kosong
    resp_empty = _recap(client, world, "finance", month="2000-01")
    assert resp_empty.status_code == 200
    assert resp_empty.json() == []


def test_recap_permissions(client, world: World):
    """Finance, OPS, Admin: seluruh organisasi. PM: hanya unit yang dipegangnya (keputusan pemilik).
    Peran lain: 403."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    ot_id = _report(client, world, plan_id, "leader", hours=2.0).json()["id"]
    assert _review(client, world, ot_id, "pm", decision="APPROVED").status_code == 200
    other_unit = world.add_unit("LAIN")
    world.add_person("pm_other", "PM", other_unit, per_unit=True)

    assert _recap(client, world, "finance").status_code == 200
    assert _recap(client, world, "ops").status_code == 200
    assert _recap(client, world, "admin").status_code == 200
    own_unit = _recap(client, world, "pm")
    assert own_unit.status_code == 200
    assert [(r["employee_id"], r["approved_hours"]) for r in own_unit.json()] == [(world.employees["leader"], 2.0)]
    other = _recap(client, world, "pm_other")
    assert other.status_code == 200 and other.json() == []

    for who in ("member", "leader", "asset", "hr"):
        resp = _recap(client, world, who)
        assert resp.status_code == 403, f"Diharapkan 403 untuk {who}, dapat {resp.status_code}"
        assert resp.json()["error"]["message"] == "Rekap lembur hanya untuk Finance, OPS, Admin, atau PM unit."


@pytest.mark.parametrize("bad_month", ["2026", "26-09", "2026/09", "abcd-ef"])
def test_recap_invalid_month_format(client, world: World, bad_month: str):
    """Month bukan format YYYY-MM → 422."""
    resp = _recap(client, world, "finance", month=bad_month)
    assert resp.status_code == 422, f"Diharapkan 422 untuk month={bad_month}"


# ---------------------------------------------------------------------------
# 5. Regresi R2: unit filter — PM unit lain tidak melihat lembur unit ini
# ---------------------------------------------------------------------------

def test_r2_pm_other_unit_cannot_see_plan(client, world: World):
    """R2: PM unit CCTV tidak melihat SK unit Wall Display → overtime juga tidak terlihat."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    _report(client, world, plan_id, "leader")

    unit2 = world.add_unit("WALLD")
    world.add_person("pm_walld", "PM", unit2, per_unit=True)

    resp = _list(client, world, plan_id, "pm_walld")
    assert resp.status_code == 404  # SK tidak terlihat oleh PM unit lain
