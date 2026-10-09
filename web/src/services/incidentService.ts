import { useQuery, useQueryClient } from "@tanstack/react-query";
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

/** POST /hse/incidents — laporkan insiden/HSE (bukti sudah diunggah, berupa file_id). */
/** Kategori & tingkat dari form (string) — nilainya diperiksa server. */
type IncidentCreateInput = Omit<components["schemas"]["IncidentCreate"], "category" | "severity"> & { category: string; severity: string };

export async function createIncident(body: IncidentCreateInput): Promise<Incident> {
  return (await api.post<Incident>("/hse/incidents", body)).data;
}

/** POST /hse/incidents/{id}/resolve — tandai insiden selesai ditangani. */
export async function resolveIncident(id: string, body: components["schemas"]["IncidentResolve"]): Promise<Incident> {
  return (await api.post<Incident>(`/hse/incidents/${id}/resolve`, body)).data;
}

/** Simpan insiden baru/terubah ke cache daftar insiden rencana kerja (paling atas). */
export function useStoreIncident(planId: string) {
  const qc = useQueryClient();
  return (inc: Incident) =>
    qc.setQueryData<Incident[]>(key(planId), (old = []) => [inc, ...old.filter((i) => i.id !== inc.id)]);
}
