import { useQuery } from "@tanstack/react-query";
import { fetchFileUrl } from "@/services/fileService";

/**
 * Mengambil URL API bertiket untuk sebuah berkas.
 *
 * `<img src="/api/v1/files/{id}">` tidak bisa dipakai karena permintaan gambar oleh browser
 * tidak menyertakan header Authorization; API hanya melayani berkas terautentikasi.
 * Karena itu URL bertanda tangan (berlaku 5 menit) diambil lewat axios lalu dipasang sebagai src.
 */
export function useFileUrl(fileId: string | null | undefined, variant: "thumb" | "view" | "full" = "view") {
  return useQuery({
    queryKey: ["fileUrl", fileId, variant],
    enabled: Boolean(fileId),
    staleTime: 4 * 60 * 1000, // presigned URL berlaku 5 menit
    queryFn: async () => (await fetchFileUrl(fileId as string, variant)).url,
  });
}
