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
 * `scopes` = peran + kantor yang sudah dimiliki; `officeId` = kantor yang dipilih. Duplikat ditolak
 * hanya bila peran dan kantor sama (OM berlaku semua kantor). Kantor tidak diketahui: biarkan server memutuskan.
 */
export function roleAddBlocker(opts: {
  role: string;
  primaryRole?: string | null;
  held: string[];
  scopes?: { role: string; office_id?: string | null }[];
  officeId?: string | null;
  extraCount: number;
  isSelf: boolean;
}): string | null {
  const { role, primaryRole, held, scopes = [], officeId, extraCount, isSelf } = opts;
  if (isSelf) return "Anda tidak dapat mengubah peran akun sendiri.";
  if (primaryRole === "SUPER_ADMIN") return "Super Admin tidak digabung dengan peran lain.";
  if (extraCount >= MAX_EXTRA_ROLES) return `Paling banyak ${MAX_EXTRA_ROLES} peran tambahan. Cabut satu peran dulu.`;
  const sameRole = scopes.filter((x) => x.role === role);
  const duplicate = needsOffice(role)
    ? !!officeId && sameRole.some((x) => x.office_id === officeId)
    : sameRole.length > 0 || (scopes.length === 0 && held.includes(role));
  if (duplicate) return "Orang ini sudah memegang peran itu di kantor yang sama.";
  const pair = role === "ADMIN_HR_GA" ? "FINANCE" : role === "FINANCE" ? "ADMIN_HR_GA" : null;
  if (pair && held.includes(pair)) return "HR dan Finance tidak boleh dipegang bersamaan oleh satu orang.";
  return null;
}

/** Baris "Peran · berlaku untuk kantor X" dari role_scopes; kosong bila field tidak ada (tampilan lama). */
export function roleScopeLines(me: (Pick<Me, "role_scopes"> & { role?: string }) | null | undefined): string[] {
  const scopes = me?.role_scopes;
  if (!scopes || scopes.length === 0) return [];
  // Peran utama sudah tampil sebagai label; jangan ulangi tanpa keterangan kantor.
  const utama = me?.role ? roleName(me.role) : null;
  return scopes
    .filter((s) => s.office_name || roleName(s.role) !== utama)
    .map((s) => (s.office_name ? `${roleName(s.role)} · berlaku untuk kantor ${s.office_name}` : roleName(s.role)));
}
