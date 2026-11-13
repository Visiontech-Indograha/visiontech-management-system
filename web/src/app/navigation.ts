import {
  Bed,
  Network,
  Settings,
  BookUser,
  Briefcase,
  Building2,
  CalendarDays,
  CalendarRange,
  Clock,
  Fingerprint,
  ChartColumn,
  ClipboardList,
  FileClock,
  FolderOpen,
  IdCard,
  Hourglass,
  Timer,
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
  { path: "/attendance", label: "Absensi", icon: Clock, group: "Kehadiran dan SDM" },
  { path: "/leaves", label: "Cuti dan Izin", icon: CalendarDays, group: "Kehadiran dan SDM" },
  { path: "/hikvision", label: "Mesin absensi", icon: Fingerprint, requires: ["manage:hikvision"], group: "Kehadiran dan SDM" },
  { path: "/attendance-recap", label: "Rekap bulanan", icon: ChartColumn, group: "Kehadiran dan SDM" },
  { path: "/overtime", label: "Lembur", icon: Hourglass, group: "Kehadiran dan SDM" },
  { path: "/overtime-recap", label: "Rekap lembur", icon: Timer, anyOf: ["review:overtime", "create:plan"], group: "Kehadiran dan SDM" },
  // 3. Aset & Fasilitas
  { path: "/assets", label: "Kendaraan dan alat", icon: Truck, group: "Aset dan Fasilitas" },
  { path: "/vehicle-documents", label: "Dokumen kendaraan", icon: FileClock, anyOf: ["view:vehicle_documents", "manage:vehicle_documents"], group: "Aset dan Fasilitas" },
  { path: "/mess", label: "Mess Karyawan", icon: Bed, requires: ["view:mess"], group: "Aset dan Fasilitas" },
  // 4. SDM & Direktori
  { path: "/my-documents", label: "Berkas saya", icon: FolderOpen, requires: ["view:documents"], group: "Karyawan dan Berkas" },
  { path: "/dokumen-saya", label: "Dokumen saya", icon: IdCard, group: "Karyawan dan Berkas" },
  { path: "/directory", label: "Direktori", icon: BookUser, requires: ["view:users"], group: "Karyawan dan Berkas" },
  { path: "/offboarding", label: "Offboarding", icon: UserMinus, requires: ["view:offboarding"], group: "Karyawan dan Berkas" },
  // 5. Master & Sistem
  { path: "/sites", label: "Lokasi kerja", icon: MapPin, requires: ["manage:sites"], group: "Master dan Sistem" },
  { path: "/work-types", label: "Jenis pekerjaan", icon: ListChecks, requires: ["create:plan"], group: "Master dan Sistem" },
  { path: "/divisions", label: "Divisi dan jabatan", icon: Network, anyOf: ["manage:divisions", "manage:users"], group: "Master dan Sistem" },
  { path: "/audit-logs", label: "Audit log", icon: ScrollText, requires: ["view:audit"], group: "Master dan Sistem" },
  { path: "/system-settings", label: "Setelan sistem", icon: Settings, requires: ["manage:system_settings"], group: "Master dan Sistem" },
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
