/**
 * Calon Project Manager: karyawan yang peran utamanya PM.
 * Catatan: daftar karyawan API hanya memuat peran utama (`system_role`), belum peran tambahan.
 */
export function pmCandidates<T extends { system_role?: string | null }>(items: readonly T[] | undefined): T[] {
  return (items ?? []).filter((e) => e.system_role === "PROJECT_MANAGER");
}
