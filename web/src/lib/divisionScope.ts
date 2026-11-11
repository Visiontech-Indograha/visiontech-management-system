import type { Me } from "@/lib/types";

/**
 * Divisi yang boleh dipilih pengguna pada Tugas Klien (WO).
 * Project Manager hanya melihat divisinya sendiri; OM, SA, dan peran lain tidak dibatasi (null).
 */
export function divisionScopeIds(me: Me | null | undefined): string[] | null {
  if (!me) return null;
  if (me.role !== "PROJECT_MANAGER" && me.role !== "PM") return null;
  if (me.managed_division_ids && me.managed_division_ids.length > 0) return me.managed_division_ids;
  return me.division_id ? [me.division_id] : [];
}

/** Bawaan filter papan WO: divisi milik pengguna bila ada di cakupan, selain itu "" (semua divisi dalam cakupan). */
export function defaultBoardDivisionId(me: Me | null | undefined): string {
  const scope = divisionScopeIds(me);
  if (!scope || !me?.division_id) return "";
  return scope.includes(me.division_id) ? me.division_id : "";
}
