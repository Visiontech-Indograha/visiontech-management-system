import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type WorkType = components["schemas"]["WorkTypeOut"];
export type WorkTypeInput = components["schemas"]["WorkTypeIn"];

const KEY = ["work-types"] as const;

/** GET /work-types — yang aktif; `all` (butuh izin create:plan) menyertakan yang nonaktif. */
export const useWorkTypes = (all = false) =>
  useQuery({
    queryKey: [...KEY, { all }],
    queryFn: async () => (await api.get<WorkType[]>("/work-types", { params: all ? { all: true } : {} })).data,
  });

export function useSaveWorkType(id?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: WorkTypeInput) =>
      id ? (await api.put<WorkType>(`/work-types/${id}`, body)).data : (await api.post<WorkType>("/work-types", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

/** DELETE /work-types/{id} menonaktifkan (rencana kerja lama tetap utuh). */
export function useDeactivateWorkType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/work-types/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
