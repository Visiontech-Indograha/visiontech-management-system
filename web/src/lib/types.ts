import type { components } from "./api-types";

type S = components["schemas"];

export type Me = S["MeOut"];
export type TokenOut = S["TokenOut"];
export type UserOut = S["UserOut"];
export type UserCreated = S["UserCreated"];
export type UserCreate = S["UserCreate"];
export type UserUpdate = S["UserUpdate"];
export type AuditLogOut = S["AuditLogOut"];
export type UserPage = S["Page_UserOut_"];
export type AuditPage = S["Page_AuditLogOut_"];

export const ROLE_LABEL: Record<string, string> = {
  super_admin: "Super Admin",
  admin: "Admin",
  team_leader: "Team Leader",
  finance: "Finance",
  hes: "HES",
  user: "User",
  WTL: "WTL",
  DRIVER: "Driver",
};

export const EMPLOYMENT_LABEL: Record<string, string> = {
  PERMANENT: "Tetap",
  CONTRACT: "Kontrak",
};
