import type { Me } from "@/lib/types";
import { PERMISSIONS, type Permission } from "@/lib/permissions";

/** Menyamai BASE_PERMISSIONS dan _ROLE_EXTRA di api/app/core/permissions.py. */
const BASE: Permission[] = ["view:users", "view:documents", "upload:documents"];

export const MOCK_PERMISSIONS: Record<string, Permission[]> = {
  ADMIN: [...PERMISSIONS],
  HR: [...BASE, "manage:users", "verify:documents", "manage:employee_documents"],
  PM: [...BASE, "create:plan", "publish:plan", "view:timeline"],
  FINANCE: [...BASE, "review:attendance", "review:overtime"],
  ASSET: [...BASE, "manage:assets"],
  OPS: [...BASE, "create:plan", "publish:plan", "review:overtime", "view:timeline", "view:audit"],
  field: BASE,
};

export function mockMe(key: string | undefined): Me | null {
  if (!key || !(key in MOCK_PERMISSIONS)) return null;
  return {
    user_id: "00000000-0000-0000-0000-000000000000",
    email: `${key.toLowerCase()}@example.com`,
    role: key,
    permissions: MOCK_PERMISSIONS[key],
  };
}
