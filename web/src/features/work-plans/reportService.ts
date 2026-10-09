import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { planKey } from "./workPlanService";

export type TeamMember = components["schemas"]["TeamMemberOut"];
export type FinalReport = components["schemas"]["FinalReportOut"];

/** Tim aktif SK (GET /work-plans/{id}/members) — kunci di bawah planKey agar ikut segar setelah transisi. */
export const usePlanTeam = (planId: string) =>
  useQuery({
    queryKey: [...planKey(planId), "team"],
    queryFn: async () => (await api.get<TeamMember[]>(`/work-plans/${planId}/members`)).data,
  });

/** Laporan akhir (GET /work-plans/{id}/completion) — null bila belum diajukan. */
export const useFinalReport = (planId: string, enabled = true) =>
  useQuery({
    queryKey: [...planKey(planId), "completion"],
    enabled,
    queryFn: async () => (await api.get<FinalReport | null>(`/work-plans/${planId}/completion`)).data,
  });

export type PlanAsset = components["schemas"]["PlanAssetItem"];

/** Aset yang dipakai SK + kondisi saat dikembalikan (GET /work-plans/{id}/assets) — mode presentasi. */
export const usePlanAssets = (planId: string, enabled = true) =>
  useQuery({
    queryKey: [...planKey(planId), "assets"],
    enabled,
    queryFn: async () => (await api.get<PlanAsset[]>(`/work-plans/${planId}/assets`)).data,
  });

