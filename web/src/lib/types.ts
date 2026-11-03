import type { components } from "./apiTypes";

type S = components["schemas"];

/** Respons GET /auth/me sesuai API terbaru: {user_id, email, role, permissions[]}. */
export interface ManagedDivision {
  division_id: string;
  name: string;
  is_pm?: boolean;
  is_om?: boolean;
}

export type Me = S["AuthUserMeResponseSchema"] & {
  managed_division_ids?: string[];
  managed_divisions?: ManagedDivision[];
};
export type TokenOut = S["AuthLoginResponseSchema"];

/** Label peran sesuai RoleCode API. */
export const ROLE_LABEL: Record<string, string> = {
  SUPER_ADMIN: "Super Admin",
  OPERATIONAL_MANAGER: "Operational Manager",
  PROJECT_MANAGER: "Project Manager",
  TEAM_LEADER: "Team Leader",
  ADMIN_HR_GA: "Admin HR & GA",
  EMPLOYEE: "Karyawan / Teknisi",
  ADMIN: "Admin",
  HR: "HR",
  PM: "Project Manager",
  FINANCE: "Finance",
  ASSET: "Asset",
  OPS: "Operasional",
  field: "Karyawan lapangan",
};
