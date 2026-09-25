import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

export type Site = components["schemas"]["SiteResponse"];
export type SiteCreate = components["schemas"]["SiteCreate"];

const KEY = ["sites"] as const;

/** GET /sites mengembalikan daftar biasa (tanpa paginasi), urut nama. */
export const useSites = () =>
  useQuery({ queryKey: KEY, queryFn: async () => (await api.get<Site[]>("/sites")).data });

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
