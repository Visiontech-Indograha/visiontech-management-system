import {
  Bed,
  BookUser,
  CalendarRange,
  Clock,
  ChartColumn,
  ClipboardList,
  FolderOpen,
  Hourglass,
  House,
  ListChecks,
  MapPin,
  Truck,
  ScrollText,
  UserMinus,
  Users,
  type LucideIcon,
} from "lucide-react";
import type { Permission } from "@/lib/permissions";

export interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  requires?: Permission[];
  anyOf?: Permission[];
  group?: string;
}

/** Menu web memakai izin yang dikirim /auth/me; API tetap menegakkan otorisasi. */
export const NAV_ITEMS: NavItem[] = [
  { path: "/", label: "Beranda", icon: House },
  { path: "/work-plans", label: "Work plan", icon: ClipboardList },
  { path: "/teams", label: "Tim Lapangan", icon: Users, requires: ["view:teams"] },
  { path: "/timeline", label: "Timeline tim", icon: CalendarRange, requires: ["view:timeline"] },
  { path: "/attendance", label: "Absensi", icon: Clock },
  { path: "/attendance-recap", label: "Rekap absensi", icon: ChartColumn },
  { path: "/overtime-recap", label: "Rekap lembur", icon: Hourglass, anyOf: ["review:overtime", "create:plan"] },
  { path: "/assets", label: "Kendaraan & alat", icon: Truck },
  { path: "/mess", label: "Mess Karyawan", icon: Bed, requires: ["view:mess"] },
  { path: "/my-documents", label: "Berkas saya", icon: FolderOpen, requires: ["view:documents"] },
  { path: "/directory", label: "Direktori", icon: BookUser, requires: ["view:users"] },
  { path: "/offboarding", label: "Offboarding", icon: UserMinus, requires: ["view:offboarding"] },
  { path: "/sites", label: "Lokasi kerja", icon: MapPin, requires: ["manage:sites"] },
  { path: "/work-types", label: "Jenis pekerjaan", icon: ListChecks, requires: ["create:plan"] },
  { path: "/audit-logs", label: "Audit log", icon: ScrollText, requires: ["view:audit"] },
];

export function isAllowed(item: NavItem, permissions: readonly string[]): boolean {
  return (
    (item.requires ?? []).every((permission) => permissions.includes(permission)) &&
    (!item.anyOf || item.anyOf.some((permission) => permissions.includes(permission)))
  );
}

export function visibleNav(permissions: readonly string[]): NavItem[] {
  return NAV_ITEMS.filter((item) => isAllowed(item, permissions));
}
