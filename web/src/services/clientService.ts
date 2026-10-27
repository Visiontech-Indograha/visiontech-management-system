import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";

export interface Client {
  client_id: string;
  client_code: string;
  name: string;
  pic_name?: string | null;
  pic_phone?: string | null;
  address?: string | null;
  status: boolean;
  project_count: number;
}

export interface ClientInput {
  client_code: string;
  name: string;
  pic_name?: string | null;
  pic_phone?: string | null;
  address?: string | null;
}

const KEY = ["clients"] as const;

export const useClients = (activeOnly = true, q?: string) =>
  useQuery({
    queryKey: [...KEY, { activeOnly, q }],
    queryFn: async () =>
      (
        await api.get<Client[]>("/clients", {
          params: { active_only: activeOnly, ...(q ? { q } : {}) },
        })
      ).data,
  });

export function useSaveClient(id?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ClientInput) =>
      id
        ? (await api.put<Client>(`/clients/${id}`, body)).data
        : (await api.post<Client>("/clients", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteClient() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/clients/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
