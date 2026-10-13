import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type WeeklyReport = components["schemas"]["WeeklyReportResponse"];
export type WeeklyReportRequest = components["schemas"]["WeeklyReportRequest"];
export type WeeklyReviewRequest = components["schemas"]["WeeklyReviewRequest"];

const weekPath = (planId: string, week: number) => `/work-plans/${planId}/weekly/${week}`;

/** GET /work-plans/{id}/weekly — laporan mingguan per minggu ke-N. */
export async function listWeeklyReports(planId: string): Promise<WeeklyReport[]> {
  return (await api.get<WeeklyReport[]>(`/work-plans/${planId}/weekly`)).data;
}

/** PUT …/weekly/{week} — simpan draf laporan mingguan ketua. */
export async function saveWeeklyReport(planId: string, week: number, body: WeeklyReportRequest): Promise<WeeklyReport> {
  return (await api.put<WeeklyReport>(weekPath(planId, week), body)).data;
}

/** POST …/weekly/{week}/submit — kirim laporan mingguan ke PM. */
export async function submitWeeklyReport(planId: string, week: number): Promise<WeeklyReport> {
  return (await api.post<WeeklyReport>(`${weekPath(planId, week)}/submit`)).data;
}

/** POST …/weekly/{week}/review — PM menyetujui / meminta perbaikan. */
export async function reviewWeeklyReport(planId: string, week: number, body: WeeklyReviewRequest): Promise<WeeklyReport> {
  return (await api.post<WeeklyReport>(`${weekPath(planId, week)}/review`, body)).data;
}
