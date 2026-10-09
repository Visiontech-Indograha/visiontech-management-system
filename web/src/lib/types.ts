import type { components } from "./apiTypes";

type S = components["schemas"];

/** Respons GET /auth/me sesuai API terbaru: {user_id, email, role, permissions[]}. */
export type Me = S["UserMeResponse"];
export type TokenOut = S["TokenResponse"];

/** Label peran sesuai RoleCode API. */
export const ROLE_LABEL: Record<string, string> = {
  ADMIN: "Admin",
  HR: "HR",
  PM: "Project Manager",
  FINANCE: "Finance",
  ASSET: "Asset",
  OPS: "Operasional",
  field: "Karyawan lapangan",
};
