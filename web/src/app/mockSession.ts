import type { Me } from "@/lib/types";

const PROJECT = "master:item_project";

const COMMON_OWN = ["employee_document:read_own", "attendance:submit", "attendance:read_own"];

/** Peta role → permission sementara, mengikuti docs/02-SRS §5.2. Diganti GET /me pada Fase 1. */
export const MOCK_PERMISSIONS: Record<string, string[]> = {
  super_admin: [
    "user:manage", "employee:read", "employee:profile_update", "document_type:manage",
    "employee_document:manage", "document_alert:read", "attendance:read_all", "attendance:correct",
    "attendance:export", "team:manage", "work_plan:read", "progress:read", "vehicle_loan:read",
    "issuance:project_goods", "issuance:tool_ppe", "master:product", "master:vehicle", PROJECT,
    "master:item_tool_ppe", "master:site", "report:pdf", "dashboard:overview", "audit:read",
  ],
  admin: [
    ...COMMON_OWN, "employee:read", "document_alert:read", "vehicle_loan:read",
    "issuance:project_goods", "master:product", "master:vehicle", PROJECT, "master:site",
    "dashboard:overview",
  ],
  team_leader: [
    ...COMMON_OWN, "employee:read", "document_alert:read", "attendance:read_team", "attendance:correct",
    "team:manage", "work_plan:manage", "work_plan:read", "progress:read", "vehicle_loan:approve",
    "vehicle_loan:read", "master:product", "master:vehicle", "master:site", "report:pdf",
    "dashboard:overview",
  ],
  finance: [
    ...COMMON_OWN, "employee:read", "document_alert:read", "attendance:read_all", "attendance:export",
    "dashboard:overview",
  ],
  hes: [
    ...COMMON_OWN, "employee:read", "employee:profile_update", "document_type:manage",
    "employee_document:manage", "document_alert:read", "issuance:tool_ppe", "master:item_tool_ppe",
    "dashboard:overview",
  ],
  wtl: [
    ...COMMON_OWN, "work_plan:read", "progress:submit", "progress:read", "issuance:read_own",
    "master:product", "master:site",
  ],
  driver: [
    ...COMMON_OWN, "work_plan:read", "vehicle_loan:create_return", "vehicle_loan:read",
    "issuance:read_own", "master:product", "master:vehicle", "master:site",
  ],
};

const ROLE_OF: Record<string, Pick<Me, "role" | "user_type">> = {
  super_admin: { role: "super_admin", user_type: null },
  admin: { role: "admin", user_type: null },
  team_leader: { role: "team_leader", user_type: null },
  finance: { role: "finance", user_type: null },
  hes: { role: "hes", user_type: null },
  wtl: { role: "user", user_type: "WTL" },
  driver: { role: "user", user_type: "DRIVER" },
};

export function mockMe(key: string | undefined): Me | null {
  if (!key || !(key in MOCK_PERMISSIONS)) return null;
  return {
    id: "00000000-0000-0000-0000-000000000000",
    username: key,
    full_name: `Pengguna contoh (${key})`,
    ...ROLE_OF[key],
    permissions: MOCK_PERMISSIONS[key],
    manage_permissions: MOCK_PERMISSIONS[key], // pratinjau dev: semua dianggap hak penuh
    must_change_password: false,
    documents_incomplete: { count: 0, missing: [] },
  };
}
