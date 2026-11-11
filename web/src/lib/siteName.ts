/** Apakah nama lokasi sudah dipakai lokasi lain (tanpa membedakan huruf besar/kecil). Hanya peringatan, bukan blokir. */
export function duplicateSiteName(
  name: string,
  sites: readonly { id: string; name: string }[] | undefined,
  selfId?: string,
): boolean {
  const n = name.trim().toLowerCase();
  if (!n) return false;
  return (sites ?? []).some((s) => s.id !== selfId && s.name.trim().toLowerCase() === n);
}

const text = (v: number | null | undefined) => (v == null ? "" : String(v));

/** Nilai awal formulir lokasi kerja (kosong untuk tambah, terisi untuk ubah). */
export function siteFormDefaults(site?: {
  name: string; address?: string | null; location?: { lat?: number | null; lng?: number | null } | null; radius_m: number;
}) {
  return {
    name: site?.name ?? "",
    address: site?.address ?? "",
    lat: text(site?.location?.lat),
    lng: text(site?.location?.lng),
    radius_m: String(site?.radius_m ?? 50),
  };
}
