/** Nama permission sesuai backend terbaru (api/app/core/permissions.py). */
export const PERMISSIONS = [
  "manage:users",
  "view:users",
  "upload:documents",
  "view:documents",
  "manage:employee_documents",
  "verify:documents",
  "create:plan",
  "publish:plan",
  "review:attendance",
  "review:unit_attendance",
  "review:overtime",
  "manage:assets",
  "view:timeline",
  "view:audit",
  "run:system_jobs",
] as const;

export type Permission = (typeof PERMISSIONS)[number];
