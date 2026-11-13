import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import { uploadFiles } from "@/services/uploadService";

type S = components["schemas"];
export type Inspection = S["VehicleInspectionResponse"];
export type ChecklistTemplate = S["InspectionChecklistTemplate"];

export const INSPECTION_KEY = ["vehicle-inspections"] as const;
export const INSPECTION_LIST_URL = "/hse/inspections";
export const INSPECTION_MINE_URL = "/hse/inspections/mine";

export const useChecklistTemplate = () =>
  useQuery({
    queryKey: [...INSPECTION_KEY, "template"],
    queryFn: async () => (await api.get<ChecklistTemplate>("/hse/inspections/checklist-template")).data,
    staleTime: 10 * 60 * 1000,
  });

export const useInspection = (id: string | null) =>
  useQuery({
    queryKey: [...INSPECTION_KEY, "detail", id],
    enabled: Boolean(id),
    queryFn: async () => (await api.get<Inspection>(`/hse/inspections/${id}`)).data,
  });

export interface NewInspection {
  body: Omit<S["VehicleInspectionCreate"], "photos_json">;
  photos: File[];
}

/** Unggah foto satu per satu lebih dulu, lalu kirim formulir dengan id berkasnya. */
export function useCreateInspection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ body, photos }: NewInspection) => {
      const photos_json = photos.length ? await uploadFiles(photos) : [];
      return (await api.post<Inspection>("/hse/inspections", { ...body, photos_json })).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: INSPECTION_KEY }),
  });
}

/** Persetujuan: tidak optimistic; daftar dan detail disegarkan setelah sukses. */
export function useVerifyInspection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status, notes }: { id: string; status: "VERIFIED" | "REJECTED"; notes?: string }) =>
      (await api.patch<Inspection>(`/hse/inspections/${id}/verify`, { status, notes: notes || null })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: INSPECTION_KEY }),
  });
}
