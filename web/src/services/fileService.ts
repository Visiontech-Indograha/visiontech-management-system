import { api } from "@/lib/apiClient";

/** URL bertanda tangan berumur pendek untuk sebuah berkas + jenis MIME-nya. */
export interface FileUrlResponse {
  url: string;
  mime_type: string;
}

/** GET /files/{id}/url?variant= — `thumb` (pratinjau kecil), `view` (layar), atau `full` (unduh asli). */
export async function fetchFileUrl(fileId: string, variant: string): Promise<FileUrlResponse> {
  return (await api.get<FileUrlResponse>(`/files/${fileId}/url?variant=${variant}`)).data;
}
