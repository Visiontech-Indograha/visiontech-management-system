import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type DivisionRow = S["DivisionOut"];
export type DivisionBody = S["DivisionCreate"];
export type DivisionPatch = S["DivisionUpdate"];
export type PositionRow = S["JobPositionOut"];
export type PositionCreate = S["JobPositionCreate"];
export type PositionPatch = S["JobPositionUpdate"];
type PersonRow = Pick<S["EmployeeOut"], "employee_id" | "employee_no" | "full_name">;

const DIV_KEY = ["divisions"] as const;
const POS_KEY = ["job-positions"] as const;

/** Divisi dan jabatan saling terkait (jumlah tim, jumlah karyawan), jadi keduanya disegarkan bersama. */
function refresh(qc: QueryClient) {
  return Promise.all([qc.invalidateQueries({ queryKey: DIV_KEY }), qc.invalidateQueries({ queryKey: POS_KEY })]);
}

/** GET /divisions: semua divisi aktif (API tidak punya q/paginasi untuk divisi). */
export const useDivisionRows = () =>
  useQuery({ queryKey: [...DIV_KEY, "admin"], queryFn: async () => (await api.get<DivisionRow[]>("/divisions")).data });

/** GET /job-positions: semua jabatan aktif (API tidak punya q/paginasi untuk jabatan). */
export const usePositionRows = () =>
  useQuery({ queryKey: [...POS_KEY, "admin"], queryFn: async () => (await api.get<PositionRow[]>("/job-positions")).data });

/** Karyawan aktif untuk pilihan OM/PM, dicari dari awalan nama; API yang memeriksa peran saat disimpan. */
export const useDivisionPeople = (q: string) =>
  useQuery({
    queryKey: ["employees", "division-people", q],
    staleTime: 30_000,
    queryFn: async () =>
      (
        await api.get<{ items: PersonRow[] }>("/employees", {
          params: { page: 1, size: 50, status: "active", ...(q ? { q } : {}) },
        })
      ).data.items,
  });

export function useSaveDivision(id?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: DivisionBody | DivisionPatch) =>
      id ? (await api.put<DivisionRow>(`/divisions/${id}`, body)).data : (await api.post<DivisionRow>("/divisions", body)).data,
    onSuccess: () => refresh(qc),
  });
}

export function useDeleteDivision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/divisions/${id}`);
    },
    onSuccess: () => refresh(qc),
  });
}

export function useSavePosition(id?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PositionCreate | PositionPatch) =>
      id ? (await api.put<PositionRow>(`/job-positions/${id}`, body)).data : (await api.post<PositionRow>("/job-positions", body)).data,
    onSuccess: () => refresh(qc),
  });
}

export function useDeletePosition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/job-positions/${id}`);
    },
    onSuccess: () => refresh(qc),
  });
}

/** Yang sedang dihapus di layar (divisi atau jabatan). */
export type RemoveTarget = { kind: "division" | "position"; id: string; name: string };

/** Dialog tambah/ubah yang sedang terbuka. */
export type DivisionDialog =
  | { kind: "division"; item: DivisionRow | null }
  | { kind: "position"; item: PositionRow | null; divisionId: string | null };
