import {
  BookUser,
  FolderOpen,
  House,
  ScrollText,
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
  { path: "/directory", label: "Direktori", icon: BookUser, requires: ["view:users"] },
  { path: "/my-documents", label: "Berkas saya", icon: FolderOpen, requires: ["view:documents"] },
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
