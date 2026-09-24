import type { components } from "./api-types";

type S = components["schemas"];

/** Respons GET /auth/me sesuai API terbaru: {user_id, email, role, permissions[]}. */
export type Me = S["UserMeResponse"];
export type TokenOut = S["TokenResponse"];
export type UserOut = S["UserOut"];
export type UserCreated = S["UserCreated"];
export type UserCreate = S["UserCreate"];
export type UserUpdate = S["UserUpdate"];
export type AuditLogOut = S["AuditLogOut"];
export type UserPage = S["Page_UserOut_"];
export type AuditPage = S["Page_AuditLogOut_"];

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

export const EMPLOYMENT_LABEL: Record<string, string> = {
  PERMANENT: "Tetap",
  CONTRACT: "Kontrak",
};
