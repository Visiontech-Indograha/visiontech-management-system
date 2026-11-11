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
