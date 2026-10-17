import type { components } from "./apiTypes";

type S = components["schemas"];

/** Respons GET /auth/me sesuai API terbaru: {user_id, email, role, permissions[]}. */
export type Me = S["AuthUserMeResponseSchema"];
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
