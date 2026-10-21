import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type ExportRecord = components["schemas"]["ExportOut"];
export type CompletionTemplate = components["schemas"]["CompletionExportRequest"]["template"];
export type PeriodicExportBody = components["schemas"]["PeriodicExportRequest"];
export type CompletionVerification = components["schemas"]["WorkCompletionVerifyOut"];

/** Dokumen per order (docs/35 §8). `needsSignature`: hanya setelah disahkan PM. */
export const COMPLETION_TEMPLATES: { template: CompletionTemplate; label: string; needsSignature?: boolean }[] = [
  { template: "BAST", label: "Serah terima (.docx)" },
  { template: "SURVEY_REPORT", label: "Survey Report (.docx)" },
  { template: "BAST_PDF", label: "Serah terima resmi (.pdf)", needsSignature: true },
  { template: "BOQ", label: "Rekap material (.xlsx)" },
  { template: "PROGRESS_SLIDES", label: "Slide progres (.pptx)" },
];

/** Simpan Blob dari API sebagai unduhan; nama berkas dari Content-Disposition server. */
function saveBlob(data: Blob, disposition: string | undefined, fallback: string) {
  const name = /filename="([^"]+)"/.exec(disposition ?? "")?.[1] ?? fallback;
  const url = window.URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

const historyKey = (completionId: string) => ["exports", "work-completion", completionId];

export function useCompletionExports(completionId: string) {
  return useQuery({
    queryKey: historyKey(completionId),
    enabled: !!completionId,
    queryFn: async () => (await api.get<ExportRecord[]>(`/exports/work-completions/${completionId}`)).data,
  });
}

/** POST /exports/work-completions/{id}: buat dokumen, tercatat di registri, langsung terunduh. */
export function useExportCompletion(completionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (template: CompletionTemplate) => {
      const res = await api.post<Blob>(`/exports/work-completions/${completionId}`, { template }, { responseType: "blob" });
      saveBlob(res.data, res.headers["content-disposition"] as string | undefined, `${template}.bin`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: historyKey(completionId) }),
  });
}

/** POST /exports/periodic: rekap divisi per rentang (xlsx: jadwal, BoQ & uang makan; pptx: slide mingguan). */
export function useExportPeriodic() {
  return useMutation({
    mutationFn: async (body: PeriodicExportBody) => {
      const res = await api.post<Blob>("/exports/periodic", body, { responseType: "blob" });
      saveBlob(res.data, res.headers["content-disposition"] as string | undefined, "rekap.bin");
    },
  });
}

/** GET /exports/{id}/file: unduh ulang dari registri. */
export async function downloadExport(record: ExportRecord): Promise<void> {
  const res = await api.get<Blob>(`/exports/${record.export_id}/file`, { responseType: "blob" });
  saveBlob(res.data, res.headers["content-disposition"] as string | undefined, record.file_name);
}

/** GET /verify/work-completions/{id}?h= — publik (QR dokumen resmi). */
export function useVerifyCompletion(completionId: string, hash: string) {
  return useQuery({
    queryKey: ["verify", completionId, hash],
    enabled: !!completionId && /^[0-9a-f]{64}$/i.test(hash),
    retry: false,
    queryFn: async () =>
      (await api.get<CompletionVerification>(`/verify/work-completions/${completionId}`, { params: { h: hash } })).data,
  });
}
