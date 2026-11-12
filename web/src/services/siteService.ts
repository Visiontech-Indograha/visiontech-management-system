import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type Site = components["schemas"]["OfficeResponse"];
type SiteCreateSchema = components["schemas"]["OfficeCreate"];
/** Kolom ber-default di API (jam kerja, uang makan, radius kota) boleh dikosongkan saat membuat kantor. */
export type SiteCreate = Pick<SiteCreateSchema, "name" | "location"> & Partial<Omit<SiteCreateSchema, "name" | "location">>;

const KEY = ["sites"] as const;

/** GET /offices mengembalikan daftar biasa (tanpa paginasi), urut nama. */
export const useSites = () =>
  useQuery({ queryKey: KEY, queryFn: async () => (await api.get<Site[]>("/offices")).data });

/** Lokasi yang sah untuk absen peminta (R-33: kantor → lokasi kantor, lapangan → lokasi unitnya). */
export const useAttendanceSites = () =>
  useQuery({
    queryKey: [...KEY, "attendance"],
    queryFn: async () => (await api.get<Site[]>("/offices", { params: { for_attendance: true } })).data,
  });

export function useCreateSite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: SiteCreate) => (await api.post<Site>("/offices", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateSite(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<SiteCreate>) => (await api.put<Site>(`/offices/${id}`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteSite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/offices/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
