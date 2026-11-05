import { ROLE_LABEL, type Me } from "@/lib/types";

/** Peran yang boleh ditambahkan sebagai peran tambahan (sama dengan skema API RoleAssignmentCreate). */
export const EXTRA_ROLES = ["ADMIN_HR_GA", "FINANCE", "OPERATIONAL_MANAGER"] as const;
export type ExtraRole = (typeof EXTRA_ROLES)[number];
export const MAX_EXTRA_ROLES = 2;

export const EXTRA_ROLE_LABEL: Record<ExtraRole, string> = {
  ADMIN_HR_GA: "HR",
  FINANCE: "Finance",
  OPERATIONAL_MANAGER: "Operational Manager",
};

export const roleName = (role: string) => EXTRA_ROLE_LABEL[role as ExtraRole] ?? ROLE_LABEL[role] ?? role;

/** HR dan Finance wajib memilih kantor; OM otomatis semua kantor. */
export const needsOffice = (role: string) => role === "ADMIN_HR_GA" || role === "FINANCE";

/**
 * Cek di layar sebelum kirim (API tetap memeriksa). Mengembalikan pesan sederhana, atau null bila boleh.
 * `held` = peran yang sudah dimiliki (utama + tambahan), `extraCount` = jumlah peran tambahan aktif.
 */
export function roleAddBlocker(opts: {
  role: string;
  primaryRole?: string | null;
  held: string[];
  extraCount: number;
  isSelf: boolean;
}): string | null {
  const { role, primaryRole, held, extraCount, isSelf } = opts;
  if (isSelf) return "Anda tidak dapat mengubah peran akun sendiri.";
  if (primaryRole === "SUPER_ADMIN") return "Super Admin tidak digabung dengan peran lain.";
  if (extraCount >= MAX_EXTRA_ROLES) return `Paling banyak ${MAX_EXTRA_ROLES} peran tambahan. Cabut satu peran dulu.`;
  if (held.includes(role)) return "Orang ini sudah memegang peran tersebut.";
  const pair = role === "ADMIN_HR_GA" ? "FINANCE" : role === "FINANCE" ? "ADMIN_HR_GA" : null;
  if (pair && held.includes(pair)) return "HR dan Finance tidak boleh dipegang bersamaan oleh satu orang.";
  return null;
}

/** Baris "Peran · berlaku untuk kantor X" dari role_scopes; kosong bila field tidak ada (tampilan lama). */
export function roleScopeLines(me: Pick<Me, "role_scopes"> | null | undefined): string[] {
  const scopes = me?.role_scopes;
  if (!scopes || scopes.length === 0) return [];
  return scopes.map((s) => (s.office_name ? `${roleName(s.role)} · berlaku untuk kantor ${s.office_name}` : roleName(s.role)));
}
