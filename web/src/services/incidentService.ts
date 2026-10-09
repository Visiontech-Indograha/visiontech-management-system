import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type Incident = components["schemas"]["IncidentResponse"];

export const INCIDENT_CATEGORY: Record<string, string> = {
  K3_RINGAN: "K3 ringan",
  K3_BERAT: "K3 berat",
  K3_LINGKUNGAN: "K3 lingkungan",
  K3_HAMPIR: "Hampir celaka",
  ASET: "Aset",
};
export const INCIDENT_SEVERITY: Record<string, string> = { RENDAH: "Rendah", SEDANG: "Sedang", TINGGI: "Tinggi", KRITIS: "Kritis" };

/** Insiden SK (GET /hse/incidents?plan_id=) — termasuk yang dilaporkan tim dari aplikasi mobile. */
export const key = (planId: string) => ["incidents", planId] as const;
export const useSessionIncidents = (planId: string) =>
  useQuery<Incident[]>({
    queryKey: key(planId),
    queryFn: async () => (await api.get<Incident[]>("/hse/incidents", { params: { plan_id: planId } })).data,
  });

