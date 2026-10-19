import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type WorkType = components["schemas"]["WorkTypeOut"] & {
  division_id?: string | null;
  division_name?: string | null;
  description?: string | null;
};
export type WorkTypeInput = components["schemas"]["WorkTypeIn"] & {
  division_id?: string | null;
  description?: string | null;
};

const KEY = ["work-types"] as const;

/** GET /work-types — yang aktif; `all` (butuh izin create:plan) menyertakan yang nonaktif. */
export const useWorkTypes = (all = false, division_id?: string) =>
  useQuery({
    queryKey: [...KEY, { all, division_id }],
    queryFn: async () =>
      (
        await api.get<WorkType[]>("/work-types", {
          params: { ...(all ? { all: true } : {}), ...(division_id ? { division_id } : {}) },
        })
      ).data,
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

export interface DefaultMaterial {
  default_material_id: string;
  work_type_id: string;
  material_code?: string | null;
  material_name: string;
  default_qty: number;
  unit: string;
  category?: string | null;
  description?: string | null;
  sort_order: number;
  create_at?: string;
  update_at?: string;
}

export interface CreateDefaultMaterialIn {
  material_code?: string | null;
  material_name: string;
  default_qty: number;
  unit: string;
  category?: string | null;
  description?: string | null;
  sort_order?: number;
}

export interface UpdateDefaultMaterialIn {
  material_code?: string | null;
  material_name?: string | null;
  default_qty?: number;
  unit?: string;
  category?: string | null;
  description?: string | null;
  sort_order?: number;
}

export function useWorkTypeMaterials(workTypeId: string) {
  return useQuery({
    queryKey: ["work-type-materials", workTypeId],
    queryFn: async () => {
      const res = await api.get<DefaultMaterial[]>(`/work-types/${workTypeId}/materials`);
      return res.data;
    },
    enabled: !!workTypeId,
  });
}

export function useCreateWorkTypeMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      workTypeId,
      payload,
    }: {
      workTypeId: string;
      payload: CreateDefaultMaterialIn;
    }) => {
      const res = await api.post<DefaultMaterial>(
        `/work-types/${workTypeId}/materials`,
        payload
      );
      return res.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["work-type-materials", vars.workTypeId] });
      qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useUpdateWorkTypeMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: {
      materialId: string;
      workTypeId: string;
      payload: UpdateDefaultMaterialIn;
    }) => {
      const res = await api.put<DefaultMaterial>(
        `/work-types/materials/${vars.materialId}`,
        vars.payload
      );
      return res.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["work-type-materials", vars.workTypeId] });
      qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useDeleteWorkTypeMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: {
      materialId: string;
      workTypeId: string;
    }) => {
      await api.delete(`/work-types/materials/${vars.materialId}`);
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["work-type-materials", vars.workTypeId] });
      qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

