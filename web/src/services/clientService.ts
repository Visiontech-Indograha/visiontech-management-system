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

export interface ClientSite {
  site_id: string;
  client_id: string;
  site_name: string;
  address: string;
  latitude: number;
  longitude: number;
  geofence_radius_meters: number;
  pic_name?: string | null;
  pic_phone?: string | null;
}

export interface ClientSiteInput {
  site_name: string;
  address: string;
  latitude: number;
  longitude: number;
  geofence_radius_meters?: number;
  pic_name?: string | null;
  pic_phone?: string | null;
}

export const useClientSites = (clientId?: string) =>
  useQuery({
    queryKey: ["client_sites", clientId],
    queryFn: async () => {
      if (!clientId) return [];
      return (await api.get<ClientSite[]>(`/clients/${clientId}/sites`)).data;
    },
    enabled: Boolean(clientId),
  });

export function useSaveClientSite(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { siteId?: string; data: ClientSiteInput } | ClientSiteInput) => {
      const siteId = "siteId" in vars ? vars.siteId : undefined;
      const body = "data" in vars ? vars.data : vars;
      return siteId
        ? (await api.put<ClientSite>(`/clients/${clientId}/sites/${siteId}`, body)).data
        : (await api.post<ClientSite>(`/clients/${clientId}/sites`, body)).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["client_sites", clientId] }),
  });
}

export function useDeleteClientSite(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (siteId: string) => {
      await api.delete(`/clients/${clientId}/sites/${siteId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["client_sites", clientId] }),
  });
}
