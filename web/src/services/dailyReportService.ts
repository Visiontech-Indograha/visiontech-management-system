import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type PlanDay = S["PlanDayOut"];
export type DayTask = S["DayTaskOut"];
/** Isi laporan harian; `evidence` opsional saat menyimpan draf. */
export type DailyReportInput = Omit<S["DailyReportCreate"], "evidence"> & { evidence?: S["DailyReportCreate"]["evidence"] };
export type ReportReviewInput = S["ReportReviewRequest"];
export type MemberReport = S["MemberReportOut"];

const dayPath = (planId: string, dayId: string) => `/work-plans/${planId}/days/${dayId}`;

/** GET /work-plans/{id}/days — hari kerja beserta tugas & status laporannya. */
export async function listPlanDays(planId: string): Promise<PlanDay[]> {
  return (await api.get<PlanDay[]>(`/work-plans/${planId}/days`)).data;
}

/** POST …/tasks/{task}/toggle — centang/batalkan tugas harian. */
export async function toggleDayTask(planId: string, dayId: string, taskId: string): Promise<unknown> {
  return (await api.post(`${dayPath(planId, dayId)}/tasks/${taskId}/toggle`)).data;
}

/** GET …/member-reports — laporan anggota yang sudah dikirim untuk hari itu. */
export async function listMemberReports(planId: string, dayId: string): Promise<MemberReport[]> {
  return (await api.get<MemberReport[]>(`${dayPath(planId, dayId)}/member-reports`)).data;
}

/** PUT /work-plans/{id}/days/{day} — simpan draf laporan harian ketua. */
export async function saveDailyReport(planId: string, dayId: string, body: DailyReportInput): Promise<unknown> {
  return (await api.put(dayPath(planId, dayId), body)).data;
}

/** POST …/submit — kirim laporan harian ke PM. */
export async function submitDailyReport(planId: string, dayId: string): Promise<unknown> {
  return (await api.post(`${dayPath(planId, dayId)}/submit`)).data;
}

/** POST …/review — PM menyetujui / meminta perbaikan laporan harian. */
export async function reviewDailyReport(planId: string, dayId: string, body: ReportReviewInput): Promise<unknown> {
  return (await api.post(`${dayPath(planId, dayId)}/review`, body)).data;
}
