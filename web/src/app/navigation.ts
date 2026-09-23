import {
  Backpack,
  BookUser,
  CalendarCheck,
  Car,
  ClipboardCheck,
  ClipboardList,
  FileBarChart,
  FileText,
  FileWarning,
  FolderOpen,
  House,
  ListChecks,
  MapPin,
  Package,
  PackageCheck,
  ScrollText,
  Truck,
  Users,
  UsersRound,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import type { Permission } from "@/lib/permissions";

export interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  /** Semua permission ini harus dimiliki. Kosong = semua yang login. */
  requires?: Permission[];
  /** Bila diisi, minimal satu permission ini harus dimiliki. */
  anyOf?: Permission[];
  /** Disembunyikan bila user memiliki salah satu permission ini (membedakan role dengan izin bertumpuk). */
  hides?: Permission[];
  /** Super Admin adalah cadangan; menu operasional role lain tidak ditampilkan untuknya (docs/06-UI-UX §5). */
  hideForSuperAdmin?: boolean;
  group?: string;
}

/** Menu web. Hanya untuk UX; keamanan tetap ditegakkan backend. */
export const NAV_ITEMS: NavItem[] = [
  { path: "/", label: "Beranda", icon: House },
  { path: "/users", label: "Pengguna", icon: Users, requires: ["user:manage"] },
  { path: "/directory", label: "Direktori", icon: BookUser, requires: ["employee:read"] },
  {
    path: "/documents/incomplete",
    label: "Perlu dilengkapi",
    icon: FileWarning,
    requires: ["employee_document:manage"],
    hideForSuperAdmin: true,
  },
  { path: "/teams", label: "Team", icon: UsersRound, requires: ["work_plan:manage"] },
  { path: "/work-plans", label: "Work plan", icon: ClipboardList, requires: ["work_plan:manage"] },
  {
    path: "/progress",
    label: "Progress",
    icon: ListChecks,
    requires: ["work_plan:manage", "progress:read"],
  },
  {
    path: "/vehicle-approvals",
    label: "Persetujuan kendaraan",
    icon: ClipboardCheck,
    requires: ["vehicle_loan:approve"],
  },
  { path: "/reports", label: "Laporan", icon: FileBarChart, requires: ["report:pdf"], hideForSuperAdmin: true },
  { path: "/attendance", label: "Absensi", icon: CalendarCheck, requires: ["attendance:read_all"] },
  { path: "/attendance/team", label: "Absensi team", icon: CalendarCheck, requires: ["attendance:read_team"] },
  {
    path: "/issuances/goods",
    label: "Serah terima barang",
    icon: PackageCheck,
    requires: ["issuance:project_goods"],
    hideForSuperAdmin: true,
  },
  {
    path: "/issuances/tool-ppe",
    label: "Serah terima tool/APD",
    icon: Wrench,
    requires: ["issuance:tool_ppe"],
    hideForSuperAdmin: true,
  },
  {
    path: "/vehicles/status",
    label: "Status kendaraan",
    icon: Truck,
    requires: ["vehicle_loan:read"],
    hides: ["vehicle_loan:approve", "vehicle_loan:create_return"],
    hideForSuperAdmin: true,
  },
  {
    path: "/vehicles/logbook",
    label: "Logbook kendaraan",
    icon: Car,
    requires: ["vehicle_loan:create_return"],
  },
  {
    path: "/my-plan",
    label: "Plan saya",
    icon: ClipboardList,
    requires: ["work_plan:read", "progress:submit"],
  },
  { path: "/my-progress", label: "Progress", icon: ListChecks, requires: ["progress:submit"] },
  {
    path: "/team-plan",
    label: "Plan team",
    icon: ClipboardList,
    requires: ["work_plan:read"],
    hides: ["progress:submit", "work_plan:manage", "user:manage"],
  },
  { path: "/my-items", label: "Barang saya", icon: Backpack, requires: ["issuance:read_own"] },
  {
    path: "/my-documents",
    label: "Berkas saya",
    icon: FolderOpen,
    requires: ["employee_document:read_own"],
    hides: ["employee:read"],
  },
  // Master data
  { path: "/master/products", label: "Produk", icon: Package, requires: ["master:item_project"], group: "Master data" },
  { path: "/master/vehicles", label: "Kendaraan", icon: Car, requires: ["master:item_project"], group: "Master data" },
  {
    path: "/master/items-project",
    label: "Item barang",
    icon: Package,
    requires: ["master:item_project"],
    group: "Master data",
  },
  {
    path: "/master/items-tool",
    label: "Item tool/APD",
    icon: Wrench,
    requires: ["master:item_tool_ppe"],
    group: "Master data",
  },
  {
    path: "/master/document-types",
    label: "Jenis berkas",
    icon: FileText,
    requires: ["document_type:manage"],
    group: "Master data",
  },
  {
    path: "/master/sites",
    label: "Site",
    icon: MapPin,
    anyOf: ["work_plan:manage", "user:manage"],
    group: "Master data",
  },
  { path: "/audit-logs", label: "Audit log", icon: ScrollText, requires: ["audit:read"] },
];

export function isAllowed(item: NavItem, permissions: readonly string[]): boolean {
  const has = new Set(permissions);
  return (
    (item.requires ?? []).every((p) => has.has(p)) &&
    (!item.anyOf || item.anyOf.some((p) => has.has(p))) &&
    !(item.hides ?? []).some((p) => has.has(p)) &&
    !(item.hideForSuperAdmin && has.has("user:manage"))
  );
}

export function visibleNav(permissions: readonly string[]): NavItem[] {
  return NAV_ITEMS.filter((item) => isAllowed(item, permissions));
}
