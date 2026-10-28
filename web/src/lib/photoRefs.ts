export type PhotoRef = { file_id: string; requirement_id?: string | null };

/**
 * Foto realisasi/laporan tersimpan dalam dua bentuk: objek `{file_id, requirement_id}` (baru) atau
 * string id berkas saja (lama). Keduanya dinormalkan agar semua foto di DB tampil di UI.
 */
export function photoRefs(raw: unknown): PhotoRef[] {
  if (!Array.isArray(raw)) return [];
  const refs: PhotoRef[] = [];
  for (const entry of raw) {
    if (typeof entry === "string" && entry) refs.push({ file_id: entry });
    else if (entry && typeof entry === "object" && typeof (entry as PhotoRef).file_id === "string" && (entry as PhotoRef).file_id)
      refs.push(entry as PhotoRef);
  }
  return refs;
}
