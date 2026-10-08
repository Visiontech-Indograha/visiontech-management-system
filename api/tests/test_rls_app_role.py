"""
P9-2 (docs/06 Fase 9) · RLS sebagai penjaga terakhir — diuji dengan peran runtime `vms_api` (0024), bukan superuser.

Uji lain tersambung sebagai `postgres` (superuser melewati RLS), jadi kebijakan di db/03_policies.sql tidak pernah
benar-benar teruji. Di sini kueri SENGAJA tidak memfilter organisasi ("servis lupa memfilter"): RLS harus tetap
menyembunyikan baris organisasi lain, dan tanpa konteks permintaan tidak ada baris yang terlihat sama sekali.

`NO_RLS_TENANT_TABLES` mencatat tabel ber-`organization_id` yang belum dilindungi RLS — daftar hanya boleh
MENYUSUT: tabel tenant baru tanpa RLS langsung merah.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from tests.conftest import _sync_conn, sync_query

# Tabel ber-organization_id tanpa RLS (diperkecil 0025_rls_remaining_tables). Pemisahan tenant di sini sepenuhnya
# bergantung pada filter di crud. Daftar ini hanya boleh menyusut.
NO_RLS_TENANT_TABLES = {
    "app_user": "login & rotasi token mencari akun sebelum konteks organisasi ada",
}

_TENANT_TABLES_SQL = """
SELECT c.relname, c.relrowsecurity
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'vms' AND c.relkind IN ('r', 'p') AND NOT c.relispartition
   AND EXISTS (SELECT 1 FROM information_schema.columns k
                WHERE k.table_schema = 'vms' AND k.table_name = c.relname AND k.column_name = 'organization_id')
"""


@contextmanager
def _as_app(user_id: str | None, org_id: str | None) -> Iterator:
    """Kursor dengan peran `vms_api` dan konteks permintaan (SET LOCAL seperti app/db/session.py)."""
    conn = _sync_conn()
    try:
        cur = conn.cursor()
        if user_id and org_id:
            cur.execute("SELECT set_config('app.user_id', %s, true), set_config('app.organization_id', %s, true)",
                        (user_id, org_id))
        cur.execute("SET LOCAL ROLE vms_api")   # peran runtime API sejak 0024 (prod: vms_app = superuser + pemilik)
        yield cur
    finally:
        conn.rollback()
        conn.close()


def _user_id(world, who: str) -> str:
    return str(sync_query("SELECT id FROM vms.app_user WHERE login = %s", (world.logins[who],))[0][0])


def _rls_tables() -> list[str]:
    return sorted(name for name, rls in sync_query(_TENANT_TABLES_SQL) if rls)


def test_no_new_tenant_table_without_rls():
    without = {name for name, rls in sync_query(_TENANT_TABLES_SQL) if not rls}
    new = without - set(NO_RLS_TENANT_TABLES)
    assert not new, f"tabel tenant baru tanpa RLS: {sorted(new)}"
    stale = set(NO_RLS_TENANT_TABLES) - without
    assert not stale, f"sudah ber-RLS, hapus dari NO_RLS_TENANT_TABLES: {sorted(stale)}"


def test_admin_never_sees_another_organisation_even_without_a_filter(world, other_world):
    tables = _rls_tables()
    assert {"employee", "business_unit", "work_plan", "attendance", "audit_event"} <= set(tables)
    with _as_app(_user_id(world, "admin"), world.org_id) as cur:
        # Tidak vakum: data organisasi sendiri memang terlihat.
        cur.execute("SELECT count(*) FROM vms.employee")
        assert cur.fetchone()[0] == len(world.employees)
        cur.execute("SELECT count(*) FROM vms.organization")
        assert cur.fetchone()[0] == 1
        for table in tables:
            cur.execute(f"SELECT count(*) FROM vms.{table} WHERE organization_id = %s", (other_world.org_id,))
            assert cur.fetchone()[0] == 0, f"{table}: baris organisasi lain terlihat"


def test_rows_of_another_organisation_cannot_be_changed(world, other_world):
    with _as_app(_user_id(world, "admin"), world.org_id) as cur:
        cur.execute("UPDATE vms.employee SET position = 'diubah' WHERE organization_id = %s", (other_world.org_id,))
        assert cur.rowcount == 0
        cur.execute("UPDATE vms.business_unit SET name = 'diubah' WHERE organization_id = %s", (other_world.org_id,))
        assert cur.rowcount == 0
    assert sync_query("SELECT count(*) FROM vms.employee WHERE organization_id = %s AND position = 'diubah'",
                      (other_world.org_id,))[0][0] == 0


def test_without_request_context_nothing_is_visible(world):
    with _as_app(None, None) as cur:
        for table in ("employee", "business_unit", "organization", "work_plan"):
            cur.execute(f"SELECT count(*) FROM vms.{table}")
            assert cur.fetchone()[0] == 0, f"{table}: terlihat tanpa konteks permintaan"


def test_regular_member_does_not_see_other_peoples_sessions(client, world):
    for who in ("member", "leader"):
        world.headers(client, who)   # login → sesi nyata untuk keduanya
    with _as_app(_user_id(world, "member"), world.org_id) as cur:
        cur.execute("SELECT DISTINCT user_id::text FROM vms.user_session")
        assert {r[0] for r in cur.fetchall()} == {_user_id(world, "member")}


# ── Peran runtime API `vms_api` (0024_runtime_role) ────────────────────────────
def test_runtime_role_is_not_superuser_owner_or_bypassing_rls():
    (row,) = sync_query("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'vms_api'")
    assert row == (False, False)
    owners = {r[0] for r in sync_query(
        "SELECT DISTINCT pg_get_userbyid(c.relowner) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'vms' AND c.relkind IN ('r', 'p')")}
    assert "vms_api" not in owners   # pemilik tabel melewati RLS


def test_runtime_role_can_use_every_table_but_no_partition_directly():
    rows = sync_query(
        "SELECT c.relname, c.relispartition, has_table_privilege('vms_api', c.oid, 'SELECT') "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'vms' AND c.relkind IN ('r', 'p')")
    missing = sorted(name for name, part, ok in rows if not part and not ok)
    assert not missing, f"tabel baru tanpa GRANT ke vms_api (tambahkan di migrasinya): {missing}"
    direct = sorted(name for name, part, ok in rows if part and ok)
    assert not direct, f"partisi bisa dibaca langsung (RLS hanya di tabel induk): {direct}"
    assert sync_query("SELECT has_table_privilege('vms_api', 'vms.audit_event', 'UPDATE')") == [(False,)]


def test_database_functions_run_as_owner_except_pure_context_readers():
    """Aturan di trigger/fungsi DB harus melihat seluruh data organisasi (bentrok personel lintas unit, SIM, QR
    publik); dijalankan sebagai pemanggil `vms_api` aturan itu diam-diam meloloskan data yang tak terlihat."""
    rows = sync_query(
        "SELECT p.proname, p.prosecdef, array_to_string(p.proconfig, ',') FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'vms' AND p.prokind = 'f'")
    invoker = {"current_org_id", "current_user_id", "new_id"}
    not_definer = sorted(name for name, definer, _ in rows if not definer and name not in invoker)
    assert not not_definer, f"fungsi baru wajib SECURITY DEFINER SET search_path = vms, public: {not_definer}"
    loose_path = sorted(name for name, definer, cfg in rows if definer and "search_path=vms, public" not in (cfg or ""))
    assert not loose_path, f"SECURITY DEFINER tanpa search_path tetap: {loose_path}"
