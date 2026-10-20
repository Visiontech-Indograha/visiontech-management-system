import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type Site = components["schemas"]["SiteResponse"];
type SiteCreateSchema = components["schemas"]["SiteCreate"];
/** Kolom ber-default di API (jam kerja, uang makan, radius kota) boleh dikosongkan saat membuat kantor. */
export type SiteCreate = Pick<SiteCreateSchema, "name" | "location"> & Partial<Omit<SiteCreateSchema, "name" | "location">>;

const KEY = ["sites"] as const;

/** GET /sites mengembalikan daftar biasa (tanpa paginasi), urut nama. */
export const useSites = () =>
  useQuery({ queryKey: KEY, queryFn: async () => (await api.get<Site[]>("/sites")).data });

/** Lokasi yang sah untuk absen peminta (R-33: kantor → lokasi kantor, lapangan → lokasi unitnya). */
export const useAttendanceSites = () =>
  useQuery({
    queryKey: [...KEY, "attendance"],
    queryFn: async () => (await api.get<Site[]>("/sites", { params: { for_attendance: true } })).data,
  });

export function useCreateSite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: SiteCreate) => (await api.post<Site>("/sites", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteSite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/sites/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
