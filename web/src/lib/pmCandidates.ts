/**
 * Calon Project Manager: karyawan yang peran utamanya PM.
 * Catatan: daftar karyawan API hanya memuat peran utama (`system_role`), belum peran tambahan.
 * Akar "pilihan PM kosong": API mengosongkan `system_role` karyawan lain bagi yang tak berhak kolom sensitif
 * (PM tidak berhak), sehingga PM yang login tak lolos filter. Maka pengguna sendiri (bila PM) selalu disertakan.
 */
export function pmCandidates<T extends { employee_id?: string | null; system_role?: string | null }>(
  items: readonly T[] | undefined,
  self?: { role?: string | null; employee_id?: string | null } | null,
): T[] {
  const selfId = self?.role === "PROJECT_MANAGER" ? self.employee_id : null;
  return (items ?? []).filter((e) => e.system_role === "PROJECT_MANAGER" || Boolean(selfId && e.employee_id === selfId));
}

/**
 * Calon ketua tim: peran utama TEAM_LEADER (sama dengan validasi API). Bila API mengosongkan peran
 * (pemanggil tak berhak kolom sensitif, mis. PM), daftar tak disaring dan API yang memvalidasi.
 */
export function leaderCandidates<T extends { system_role?: string | null }>(items: readonly T[] | undefined): T[] {
  const list = items ?? [];
  if (!list.some((e) => e.system_role)) return [...list];
  return list.filter((e) => e.system_role === "TEAM_LEADER");
}
