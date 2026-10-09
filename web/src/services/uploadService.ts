import { api } from "@/lib/apiClient";

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

/** Unggah berkas satu per satu ke POST /files/upload; kembalikan file_id sesuai urutan. */
export async function uploadFiles(files: File[]): Promise<string[]> {
  const ids: string[] = [];
  for (const file of files) {
    const form = new FormData();
    form.set("file", file);
    ids.push((await api.post<{ file_id: string }>("/files/upload", form)).data.file_id);
  }
  return ids;
}

/** Pesan galat bila ada berkas melebihi 10 MB (docs/13), atau null. */
export function oversize(files: File[]): string | null {
  const big = files.find((f) => f.size > MAX_UPLOAD_BYTES);
  return big ? `${big.name} melebihi 10 MB.` : null;
}
