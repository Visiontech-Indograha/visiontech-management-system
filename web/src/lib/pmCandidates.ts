/**
 * Calon ketua tim: peran utama TEAM_LEADER (sama dengan validasi API). Bila API mengosongkan peran
 * (pemanggil tak berhak kolom sensitif, mis. PM), daftar tak disaring dan API yang memvalidasi.
 */
export function leaderCandidates<T extends { system_role?: string | null }>(items: readonly T[] | undefined): T[] {
  const list = items ?? [];
  if (!list.some((e) => e.system_role)) return [...list];
  return list.filter((e) => e.system_role === "TEAM_LEADER");
}
