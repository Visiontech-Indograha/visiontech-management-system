"""
Kebocoran akses (audit 2026-11): aturan cakupan per peran dan predikat SQL (`app/shared/access/scope_rules.py`).
Tanpa basis data: keputusan Python dan bentuk SQL yang memakai parameter terikat, bukan nilai pengguna.
"""
from __future__ import annotations

from app.core.permissions import permissions_for_roles
from app.core.security import CurrentUser
from app.shared.access import scope_rules as sr

EMP = "11111111-1111-1111-1111-111111111111"


def _user(*roles: str, employee_id: str | None = EMP) -> CurrentUser:
    roles_list = list(roles) or ["EMPLOYEE"]
    return CurrentUser(
        user_id="u", organization_id="o", email="e@uji", role=roles_list[0], roles=roles_list,
        session_id="s", permissions=permissions_for_roles(roles_list), employee_id=employee_id,
    )


def test_work_orders_full_scope_only_for_sa_om_and_legacy_admin_ops():
    assert sr.sees_all_work_orders(_user("SUPER_ADMIN"))
    assert sr.sees_all_work_orders(_user("OPERATIONAL_MANAGER"))
    for roles in (("PROJECT_MANAGER",), ("TEAM_LEADER",), ("EMPLOYEE",), ("ADMIN_HR_GA",), ("FINANCE",), ("HSE",)):
        assert not sr.sees_all_work_orders(_user(*roles)), roles


def test_directory_full_scope_for_hr_finance_hse_and_asset_but_not_pm_or_employee():
    for roles in (("SUPER_ADMIN",), ("OPERATIONAL_MANAGER",), ("ADMIN_HR_GA",), ("FINANCE",), ("HSE",), ("ASSET",)):
        assert sr.sees_all_employees(_user(*roles)), roles
    for roles in (("PROJECT_MANAGER",), ("TEAM_LEADER",), ("EMPLOYEE",)):
        assert not sr.sees_all_employees(_user(*roles)), roles


def test_sensitive_employee_fields_only_for_hr_om_sa():
    for roles in (("SUPER_ADMIN",), ("OPERATIONAL_MANAGER",), ("ADMIN_HR_GA",)):
        assert sr.sees_sensitive_employee_fields(_user(*roles)), roles
    for roles in (("PROJECT_MANAGER",), ("FINANCE",), ("HSE",), ("TEAM_LEADER",), ("EMPLOYEE",)):
        assert not sr.sees_sensitive_employee_fields(_user(*roles)), roles


def test_all_assets_for_sa_om_and_asset_managers_only():
    assert sr.sees_all_assets(_user("SUPER_ADMIN"))
    assert sr.sees_all_assets(_user("OPERATIONAL_MANAGER"))
    assert sr.sees_all_assets(_user("ADMIN_HR_GA"))
    assert sr.sees_all_assets(_user("ASSET"))
    assert not sr.sees_all_assets(_user("PROJECT_MANAGER"))
    assert not sr.sees_all_assets(_user("EMPLOYEE"))


def test_pm_recognised_from_system_or_legacy_role_only():
    assert sr.is_pm(_user("PROJECT_MANAGER"))
    assert sr.is_pm(_user("PM"))
    assert not sr.is_pm(_user("TEAM_LEADER"))
    assert not sr.is_pm(_user("EMPLOYEE"))


def test_viewer_params_and_asset_viewer_follow_role():
    pm = _user("PROJECT_MANAGER")
    assert sr.viewer_params(pm) == {"viewer_emp": EMP, "pm": True}
    assert sr.asset_viewer(pm) == {"viewer_emp": EMP, "pm": True}
    assert sr.asset_viewer(_user("SUPER_ADMIN")) is None
    assert sr.viewer_params(_user("EMPLOYEE", employee_id=None)) == {"viewer_emp": None, "pm": False}


def test_employee_params_carry_scope_flags():
    params = sr.employee_params(_user("EMPLOYEE"))
    assert params == {"viewer_emp": EMP, "pm": False, "dir_all": False, "sens_all": False}
    hr = sr.employee_params(_user("ADMIN_HR_GA"))
    assert hr["dir_all"] is True and hr["sens_all"] is True


def test_employee_visible_sql_covers_self_division_team_and_pm_reach():
    sql = sr.employee_visible_sql("e.employee_id")
    assert "CAST(:viewer_emp AS uuid)" in sql and "CAST(:pm AS boolean)" in sql
    assert "ve.division_id" in sql            # sesama divisi
    assert "leader_employee_id" in sql        # sesama tim
    assert "rp_d.pm_id" in sql                # jangkauan PM (pm_reach)


def test_work_order_visible_sql_uses_team_link_and_pm_division():
    sql = sr.work_order_visible_sql("wo")
    assert "wo.lead_team_id" in sql
    assert "d.pm_id = CAST(:viewer_emp AS uuid)" in sql
    assert "CAST(:pm AS boolean)" in sql


def test_asset_visible_sql_covers_holder_division_office_and_pm():
    sql = sr.asset_visible_sql("t.division_id", "t.office_id", "loan.holder_employee_id")
    assert "loan.holder_employee_id = CAST(:viewer_emp AS uuid)" in sql
    assert "t.office_id" in sql                       # aset umum di kantor pengguna
    assert "d.om_id = CAST(:viewer_emp AS uuid)" in sql


def test_scope_sql_never_interpolates_user_values():
    # Predikat hanya memuat nama kolom/alias konstan dan parameter terikat.
    for sql in (
        sr.employee_visible_sql("e.employee_id"),
        sr.employee_sensitive_sql("e.employee_id"),
        sr.work_order_visible_sql("wo"),
        sr.tool_scope_sql("t"),
        sr.vehicle_scope_sql("v"),
    ):
        assert "LIKE" not in sql.upper().replace("ILIKE", "")
        assert "'%" not in sql
        assert ":viewer_emp" in sql
