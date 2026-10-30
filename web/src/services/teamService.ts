import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type Team = S["TeamListItem"];
export type TeamDetail = S["TeamDetail"];
export type TeamMember = S["MemberOut"];
export type TeamCreate = S["TeamCreate"];

const KEY = ["teams"] as const;

export const useTeams = () =>
  useQuery({
    queryKey: KEY,
    queryFn: async () => (await api.get<Team[]>("/teams")).data,
  });

/**
 * Logo tim (hanya tampilan; penggantian dilakukan dari aplikasi mobile ketua tim).
 * Endpoint butuh header Authorization, jadi diunduh lewat axios lalu dijadikan object URL.
 */
export const useTeamLogo = (teamId: string, enabled: boolean) =>
  useQuery({
    queryKey: [...KEY, teamId, "logo"],
    enabled,
    staleTime: 5 * 60 * 1000,
    queryFn: async () => {
      const res = await api.get<Blob>(`/teams/${teamId}/logo`, { responseType: "blob" });
      return URL.createObjectURL(res.data);
    },
  });

/** Detail tim + anggota (nama, NIK, peran, nomor HP). */
export const useTeam = (id?: string | null) =>
  useQuery({
    queryKey: [...KEY, id],
    queryFn: async () => (await api.get<TeamDetail>(`/teams/${id}`)).data,
    enabled: Boolean(id),
  });

export function useCreateTeam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TeamCreate) => (await api.post<TeamDetail>("/teams", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteTeam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/teams/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useAddTeamMember(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (employeeId: string) =>
      (await api.post<TeamMember>(`/teams/${teamId}/members`, { employee_id: employeeId })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useRemoveTeamMember(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (employeeId: string) => {
      await api.delete(`/teams/${teamId}/members/${employeeId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
