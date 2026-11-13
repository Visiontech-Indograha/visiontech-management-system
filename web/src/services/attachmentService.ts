import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { oversize, uploadFiles } from "@/services/uploadService";

export type Attachment = components["schemas"]["AttachmentOut"];
export type AttachmentKind = "overtime" | "mess";

/** Batas berkas per pengajuan (sama dengan API: LAMPIRAN_PENUH). */
export const MAX_ATTACHMENTS = 5;

const path = (kind: AttachmentKind, id: string) => `/${kind}/${id}/attachments`;
const key = (kind: AttachmentKind, id: string) => ["attachments", kind, id] as const;

/** Pesan awam untuk galat lampiran; null bila bukan galat yang dikenal. */
export function attachmentErrorText(err: unknown): string | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code === "LAMPIRAN_TERKUNCI") return "Pengajuan ini sudah diputuskan atau dibatalkan, jadi lampiran tidak bisa diubah lagi.";
  if (err.code === "LAMPIRAN_PENUH") return `Lampiran sudah penuh (paling banyak ${MAX_ATTACHMENTS} berkas). Hapus satu berkas dulu.`;
  if (err.status === 403) return "Anda tidak berwenang mengubah lampiran ini.";
  if (err.status === 404) return "Pengajuan atau berkas tidak ditemukan.";
  return null;
}

export const useAttachments = (kind: AttachmentKind, id: string) =>
  useQuery({ queryKey: key(kind, id), queryFn: async () => (await api.get<Attachment[]>(path(kind, id))).data });

/** Unggah dulu (POST /files/upload), lalu tautkan file_id; API mengembalikan daftar terbaru. */
export function useAddAttachment(kind: AttachmentKind, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const big = oversize([file]);
      if (big) throw new Error(big);
      const [file_id] = await uploadFiles([file]);
      return (await api.post<Attachment[]>(path(kind, id), { file_id })).data;
    },
    onSuccess: (list) => qc.setQueryData(key(kind, id), list),
    onError: () => qc.invalidateQueries({ queryKey: key(kind, id) }),
  });
}

export function useRemoveAttachment(kind: AttachmentKind, id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (fileId: string) => {
      await api.delete(`${path(kind, id)}/${fileId}`);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: key(kind, id) }),
  });
}
