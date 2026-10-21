import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type Survey = S["SurveyOut"];
export type SurveyListItem = S["SurveyListItem"];
export type SurveyState = SurveyListItem["state"];
export type PlanFromSurvey = S["PlanFromSurveyIn"];

export const SURVEY_STATE_LABEL: Record<SurveyState, string> = {
  DRAFT: "Sedang diisi ketua tim",
  SUBMITTED: "Menunggu tinjauan",
  APPROVED: "Disetujui",
};

const KEY = ["surveys"] as const;

/** Daftar survei (docs/37): PM/OM divisinya, admin/OM semua. `state` kosong = semua. */
export const useSurveys = (state?: SurveyState) =>
  useQuery({
    queryKey: [...KEY, "list", state ?? "ALL"],
    queryFn: async () =>
      (await api.get<SurveyListItem[]>("/work-plans/surveys", { params: state ? { state } : {} })).data,
  });

export const useSurvey = (taskId: string) =>
  useQuery({
    queryKey: [...KEY, taskId],
    enabled: !!taskId,
    queryFn: async () => (await api.get<Survey>(`/work-plans/surveys/${taskId}`)).data,
  });

/** PM menyetujui / mengembalikan (catatan wajib bila dikembalikan). */
export function useReviewSurvey(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { decision: "APPROVE" | "RETURN"; note?: string | null }) =>
      (await api.post<Survey>(`/work-plans/surveys/${taskId}/review`, body)).data,
    onSuccess: (data) => {
      qc.setQueryData([...KEY, taskId], data);
      void qc.invalidateQueries({ queryKey: [...KEY, "list"] });
    },
  });
}

/** Item lanjutan per titik (persiapan + pemasangan) di jadwal DRAFT/SUBMITTED tim yang sama. */
export function usePlanFromSurvey(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PlanFromSurvey) =>
      (await api.post<{ daily_plan_id: string; created_item_ids: string[] }>(`/work-plans/surveys/${taskId}/plan`, body)).data,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["daily-plans"] }),
  });
}

/** Pratinjau laporan (PDF bila server punya konverter, selain itu .docx) sebagai Blob — tidak tercatat. */
export async function fetchSurveyPreview(taskId: string): Promise<{ blob: Blob; isPdf: boolean }> {
  const res = await api.get<Blob>(`/exports/surveys/${taskId}/preview`, { responseType: "blob" });
  return { blob: res.data, isPdf: res.headers["x-preview-format"] === "PDF" };
}

/** Laporan resmi (.docx) — tercatat di riwayat dokumen order, langsung terunduh. */
export function useOfficialSurveyReport(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await api.post<Blob>(`/exports/surveys/${taskId}`, null, { responseType: "blob" });
      const name = /filename="([^"]+)"/.exec((res.headers["content-disposition"] as string | undefined) ?? "")?.[1];
      const url = window.URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = name ?? "laporan-survei.docx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["exports"] }),
  });
}

/** Geser titik di peta titik (PM kapan pun; ketua tim selama draf) — dipakai layout otomatis laporan. */
export function useMoveSurveyPoint(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (b: { pointId: string; lat: number; lng: number }) =>
      (await api.put<Survey>(`/work-plans/surveys/points/${b.pointId}/location`, {
        site_lat: Number(b.lat.toFixed(7)),
        site_lng: Number(b.lng.toFixed(7)),
      })).data,
    onSuccess: (data) => qc.setQueryData([...KEY, taskId], data),
  });
}

export type SurveyLogo = S["SurveyLogoOut"];
const LOGO_KEY = ["survey-logos"] as const;

/** Logo kop laporan survei (perusahaan & klien) + ukuran bakunya. */
export const useSurveyLogos = () =>
  useQuery({ queryKey: LOGO_KEY, queryFn: async () => (await api.get<SurveyLogo[]>("/exports/survey-logos")).data });

export async function fetchSurveyLogo(role: string): Promise<Blob> {
  return (await api.get<Blob>(`/exports/survey-logos/${role}`, { responseType: "blob" })).data;
}

export function useSetSurveyLogo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (b: { role: string; file: File | null }) => {
      if (!b.file) return (await api.delete<SurveyLogo[]>(`/exports/survey-logos/${b.role}`)).data;
      const form = new FormData();
      form.append("file", b.file);
      return (await api.put<SurveyLogo[]>(`/exports/survey-logos/${b.role}`, form)).data;
    },
    onSuccess: (data) => {
      qc.setQueryData(LOGO_KEY, data);
      void qc.invalidateQueries({ queryKey: [...LOGO_KEY, "image"] });
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

export type SurveyLine = Survey["general_lines"][number];
export const SURVEY_UNITS = ["Unit", "Meter", "Pasang", "Batang", "Roll", "Set", "Buah", "Lot"] as const;

/** Ubah BoM survei (ketua tim saat draf, PM saat meninjau): tambah material umum, ubah/hapus baris, simpan ke katalog. */
export function useSurveyBom(taskId: string) {
  const qc = useQueryClient();
  const done = (data: Survey) => qc.setQueryData([...KEY, taskId], data);
  return {
    add: useMutation({
      mutationFn: async (b: { name: string; qty: number; unit: string }) =>
        (await api.post<Survey>(`/work-plans/surveys/${taskId}/lines`, b)).data,
      onSuccess: done,
    }),
    edit: useMutation({
      mutationFn: async (b: { bomId: string; name: string; qty: number; unit: string }) =>
        (await api.put<Survey>(`/work-plans/surveys/lines/${b.bomId}`, { name: b.name, qty: b.qty, unit: b.unit })).data,
      onSuccess: done,
    }),
    remove: useMutation({
      mutationFn: async (bomId: string) => (await api.delete<Survey>(`/work-plans/surveys/lines/${bomId}`)).data,
      onSuccess: done,
    }),
    toCatalog: useMutation({
      mutationFn: async (b: { point_type_id: string; name: string; unit: string }) =>
        (await api.post<Survey>(`/work-plans/surveys/${taskId}/catalog`, b)).data,
      onSuccess: done,
    }),
  };
}
