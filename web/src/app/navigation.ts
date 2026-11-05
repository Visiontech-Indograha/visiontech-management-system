import {
  Bed,
  BookUser,
  Briefcase,
  Building2,
  CalendarDays,
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
  ShieldCheck,
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
  // 1. Operasional Lapangan
  { path: "/work-orders", label: "Tugas Klien (WO)", icon: Briefcase, requires: ["create:plan"], group: "Operasional" },
  { path: "/work-plans", label: "Jadwal harian", icon: ClipboardList, group: "Operasional" },
  { path: "/alokasi-mingguan", label: "Alokasi mingguan", icon: CalendarRange, requires: ["create:plan"], group: "Operasional" },
  { path: "/clients", label: "Klien", icon: Building2, requires: ["create:plan"], group: "Operasional" },
  { path: "/teams", label: "Tim Lapangan", icon: Users, requires: ["view:teams"], group: "Operasional" },
  { path: "/safety-campaigns", label: "K3 / HSE", icon: ShieldCheck, anyOf: ["view:hse_campaigns", "manage:hse_campaigns"], group: "Operasional" },
  // 2. Kehadiran & Waktu
  { path: "/attendance", label: "Absensi", icon: Clock, group: "Kehadiran & SDM" },
  { path: "/leaves", label: "Cuti & Izin", icon: CalendarDays, group: "Kehadiran & SDM" },
  { path: "/attendance-recap", label: "Rekap bulanan", icon: ChartColumn, group: "Kehadiran & SDM" },
  { path: "/overtime", label: "Lembur", icon: Hourglass, group: "Kehadiran & SDM" },
  { path: "/overtime-recap", label: "Rekap lembur", icon: Hourglass, anyOf: ["review:overtime", "create:plan"], group: "Kehadiran & SDM" },
  // 3. Aset & Fasilitas
  { path: "/assets", label: "Kendaraan & alat", icon: Truck, group: "Aset & Fasilitas" },
  { path: "/mess", label: "Mess Karyawan", icon: Bed, requires: ["view:mess"], group: "Aset & Fasilitas" },
  // 4. SDM & Direktori
  { path: "/my-documents", label: "Berkas saya", icon: FolderOpen, requires: ["view:documents"], group: "Karyawan & Berkas" },
  { path: "/directory", label: "Direktori", icon: BookUser, requires: ["view:users"], group: "Karyawan & Berkas" },
  { path: "/offboarding", label: "Offboarding", icon: UserMinus, requires: ["view:offboarding"], group: "Karyawan & Berkas" },
  // 5. Master & Sistem
  { path: "/sites", label: "Lokasi kerja", icon: MapPin, requires: ["manage:sites"], group: "Master & Sistem" },
  { path: "/work-types", label: "Jenis pekerjaan", icon: ListChecks, requires: ["create:plan"], group: "Master & Sistem" },
  { path: "/audit-logs", label: "Audit log", icon: ScrollText, requires: ["view:audit"], group: "Master & Sistem" },
];

/** Tujuan utama untuk bilah navigasi bawah ponsel (< 768 px). */
export const MOBILE_PRIMARY_PATHS: readonly string[] = ["/", "/work-plans", "/attendance", "/leaves"];

export function isAllowed(item: NavItem, permissions: readonly string[]): boolean {
  return (
    (item.requires ?? []).every((permission) => permissions.includes(permission)) &&
    (!item.anyOf || item.anyOf.some((permission) => permissions.includes(permission)))
  );
}

export function visibleNav(permissions: readonly string[]): NavItem[] {
  return NAV_ITEMS.filter((item) => isAllowed(item, permissions));
}
