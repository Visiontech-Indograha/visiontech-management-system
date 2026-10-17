import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";

export interface TeamMember {
  id: string;
  team_id: string;
  employee_id: string;
  employee_name?: string;
  role_in_team?: string;
  is_active: boolean;
  assigned_at?: string;
}

export interface Team {
  id: string;
  name: string;
  leader_id: string;
  leader_name?: string;
  unit_id?: string;
  description?: string;
  is_active: boolean;
  created_at?: string;
  members?: TeamMember[];
}

export interface TeamCreate {
  name: string;
  leader_id: string;
  unit_id?: string;
  description?: string;
}

const KEY = ["teams"] as const;

export const useTeams = () =>
  useQuery({
    queryKey: KEY,
    queryFn: async () => (await api.get<Team[]>("/teams")).data,
  });

export const useTeam = (id?: string) =>
  useQuery({
    queryKey: [...KEY, id],
    queryFn: async () => (await api.get<Team>(`/teams/${id}`)).data,
    enabled: Boolean(id),
  });

export function useCreateTeam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TeamCreate) => (await api.post<Team>("/teams", body)).data,
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
    mutationFn: async (body: { employee_id: string; role_in_team?: string }) =>
      (await api.post<TeamMember>(`/teams/${teamId}/members`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useRemoveTeamMember(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (memberId: string) => {
      await api.delete(`/teams/${teamId}/members/${memberId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
