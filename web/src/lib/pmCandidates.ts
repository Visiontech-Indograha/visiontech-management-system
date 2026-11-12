/**
 * Calon Project Manager: karyawan yang peran utamanya PM.
 * Catatan: daftar karyawan API hanya memuat peran utama (`system_role`), belum peran tambahan.
 * Akar "pilihan PM kosong": API mengosongkan `system_role` karyawan lain bagi yang tak berhak kolom sensitif
 * (PM tidak berhak), sehingga PM yang login tak lolos filter. Maka pengguna sendiri (bila PM) selalu disertakan.
 */
export function pmCandidates<T extends { employee_id?: string | null; system_role?: string | null }>(
  items: readonly T[] | undefined,
  self?: { role?: string | null; employee_id?: string | null; full_name?: string | null } | null,
): T[] {
  const isPm = self?.role === "PROJECT_MANAGER" || self?.role === "PM";
  const selfId = isPm ? self?.employee_id : null;
  const out = (items ?? []).filter((e) => e.system_role === "PROJECT_MANAGER" || Boolean(selfId && e.employee_id === selfId));
  // Bila daftar karyawan tak memuat PM yang login (mis. disaring/dibatasi), pilihan tetap berisi dirinya sendiri.
  if (selfId && !out.some((e) => e.employee_id === selfId)) {
    out.push({ employee_id: selfId, full_name: self?.full_name ?? "Saya", system_role: "PROJECT_MANAGER" } as unknown as T);
  }
  return out;
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
