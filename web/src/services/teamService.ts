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

export interface TeamAvailabilityItem {
  team_id: string;
  name: string;
  division_id: string;
  division_name?: string | null;
  leader_employee_id: string;
  leader_name?: string | null;
  member_count: number;
  is_available: boolean;
  status: "AVAILABLE" | "BUSY" | "LEAVE";
  active_items_count: number;
  active_tasks: string[];
}

export const useTeamsAvailability = (workDate?: string, divisionId?: string | null) =>
  useQuery({
    queryKey: [...KEY, "availability", workDate, divisionId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (workDate) params.append("work_date", workDate);
      if (divisionId) params.append("division_id", divisionId);
      const qs = params.toString();
      const url = `/teams/availability${qs ? `?${qs}` : ""}`;
      return (await api.get<TeamAvailabilityItem[]>(url)).data;
    },
  });

export const useAvailableTeamMembers = (divisionId?: string | null) =>
  useQuery({
    queryKey: [...KEY, "available-members", divisionId],
    enabled: Boolean(divisionId),
    queryFn: async () =>
      (await api.get<Array<{ employee_id: string; full_name: string; employee_no?: string; system_role?: string }>>(
        `/teams/available-members?division_id=${divisionId}`,
      )).data,
  });

export function useRemoveTeamMember(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (employeeId: string) => {
      await api.delete(`/teams/${teamId}/members/${employeeId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
