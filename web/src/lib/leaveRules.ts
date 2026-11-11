/** Batas cuti mundur; harus sama dengan API (PR #452). */
export const LEAVE_MAX_BACKDATE_DAYS = 3;
export const LEAVE_BACKDATE_MESSAGE =
  "Tanggal mulai cuti paling lambat 3 hari ke belakang. Hubungi HR untuk cuti yang lebih lama.";
const BACKDATE_EXEMPT_ROLES = ["ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN"];

/** Tanggal hari ini di zona Jakarta (YYYY-MM-DD). `now` bisa disuntik untuk tes. */
export function jakartaToday(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(now);
}

export function isBackdateExempt(roles: Array<string | null | undefined>): boolean {
  return roles.some((r) => !!r && BACKDATE_EXEMPT_ROLES.includes(r));
}

/** Tanggal mulai paling awal; null bila tanpa batas. */
export function leaveMinStartDate(roles: Array<string | null | undefined>, now: Date = new Date()): string | null {
  if (isBackdateExempt(roles)) return null;
  const d = new Date(`${jakartaToday(now)}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - LEAVE_MAX_BACKDATE_DAYS);
  return d.toISOString().slice(0, 10);
}

/** Pesan galat bila tanggal mulai terlalu lampau, selain itu null. */
export function validateLeaveStart(start: string, roles: Array<string | null | undefined>, now: Date = new Date()): string | null {
  const min = leaveMinStartDate(roles, now);
  return min && start < min ? LEAVE_BACKDATE_MESSAGE : null;
}

/**
 * Boleh membatalkan cuti? Sama dengan API (leave_service.cancel): status menunggu/disetujui, hari terakhir belum lewat
 * (zona Jakarta); menunggu hanya oleh pemohon; sudah disetujui oleh pemohon, HR, atau OM.
 */
export function canCancelLeaveRule(
  l: { status: string; employee_id: string; end_date: string },
  me: { role?: string | null; employee_id?: string | null } | null | undefined,
  now: Date = new Date(),
): boolean {
  if (String(l.end_date).slice(0, 10) < jakartaToday(now)) return false;
  const own = Boolean(me?.employee_id) && l.employee_id === me?.employee_id;
  if (l.status === "PENDING") return own;
  const approved = l.status === "APPROVED_BY_PM" || l.status === "APPROVED_BY_HR";
  return approved && (own || ["ADMIN_HR_GA", "OPERATIONAL_MANAGER"].includes(me?.role ?? ""));
}
