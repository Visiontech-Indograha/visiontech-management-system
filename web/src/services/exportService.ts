import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { idempotencyHeaders, newIdempotencyKey } from "@/lib/idempotency";

export type ExportRecord = components["schemas"]["ExportOut"];
export type CompletionTemplate = components["schemas"]["CompletionExportRequest"]["template"];
export type PeriodicExportBody = components["schemas"]["PeriodicExportRequest"];
export type CompletionVerification = components["schemas"]["WorkCompletionVerifyOut"];
export type DailyReportBody = components["schemas"]["DailyReportExportRequest"];
export type TeamWeekBody = components["schemas"]["TeamWeekExportRequest"];

export type ExportFormat = NonNullable<components["schemas"]["DailyReportExportRequest"]["export_format"]>;

/** Pilihan format dokumen untuk pengguna awam: nama di layar dan ekstensi berkas. */
export const EXPORT_FORMATS: { value: ExportFormat; label: string; ext: string }[] = [
  { value: "PDF", label: "PDF", ext: ".pdf" },
  { value: "WORD_DOCX", label: "Word", ext: ".docx" },
  { value: "PPTX", label: "PowerPoint", ext: ".pptx" },
];

/** Dokumen per order (docs/35 §8). `needsSignature`: hanya setelah disahkan PM. */
export const COMPLETION_TEMPLATES: { template: CompletionTemplate; label: string; needsSignature?: boolean; formats?: boolean }[] = [
  { template: "ORDER_SHEET", label: "Surat tugas / lembar order", formats: true },
  { template: "BAST", label: "Serah terima", formats: true },
  { template: "SURVEY_REPORT", label: "Laporan survei", formats: true },
  { template: "BAST_PDF", label: "Serah terima resmi (.pdf)", needsSignature: true },
  { template: "BOQ", label: "Rekap material (.xlsx)" },
  { template: "PROGRESS_SLIDES", label: "Laporan kemajuan berfoto", formats: true },
];

/** Simpan Blob dari API sebagai unduhan; nama berkas dari Content-Disposition server. */
export function saveBlob(data: Blob, disposition: string | undefined, fallback: string) {
  // Utamakan nama asli UTF-8 (filename*), cadangan ASCII (filename).
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition ?? "")?.[1];
  const name = (utf8 && decodeURIComponent(utf8)) || /filename="([^"]+)"/.exec(disposition ?? "")?.[1] || fallback;
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
    mutationFn: async ({ template, format }: { template: CompletionTemplate; format?: ExportFormat }) => {
      const res = await api.post<Blob>(
        `/exports/work-completions/${completionId}`,
        format ? { template, export_format: format } : { template },
        { responseType: "blob", headers: idempotencyHeaders(newIdempotencyKey()) },
      );
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

/** POST /exports/daily-report: laporan harian satu jadwal (PDF, Word, atau PowerPoint). */
export function useExportDailyReport() {
  return useMutation({
    mutationFn: async (body: DailyReportBody) => {
      const res = await api.post<Blob>("/exports/daily-report", body, {
        responseType: "blob",
        headers: idempotencyHeaders(newIdempotencyKey()),
      });
      saveBlob(res.data, res.headers["content-disposition"] as string | undefined, "laporan-harian");
    },
  });
}

/** POST /exports/team-week: laporan mingguan tim (PDF, Word, atau PowerPoint); start_date = Senin minggu yang tampil. */
export function useExportTeamWeek() {
  return useMutation({
    mutationFn: async (body: TeamWeekBody) => {
      const res = await api.post<Blob>("/exports/team-week", body, {
        responseType: "blob",
        headers: idempotencyHeaders(newIdempotencyKey()),
      });
      saveBlob(res.data, res.headers["content-disposition"] as string | undefined, "laporan-mingguan-tim");
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
