import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";

export interface MessStay {
  mess_stay_id: string;
  mess_name: string;
  city: string;
  address: string;
  latitude: number;
  longitude: number;
  employee_id: string;
  employee_name?: string | null;
  employee_no?: string | null;
  stay_start_date: string;
  stay_end_date: string;
  create_at?: string;
}

export interface MessStayCreate {
  mess_name: string;
  city: string;
  address: string;
  latitude: number;
  longitude: number;
  employee_id: string;
  stay_start_date: string;
  stay_end_date: string;
}

export interface MessStayUpdate {
  mess_name?: string;
  city?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  stay_start_date?: string;
  stay_end_date?: string;
}

const KEY = ["mess-stays"] as const;

export const useMessStays = (filters?: { employee_id?: string; start?: string; end?: string }) =>
  useQuery({
    queryKey: [...KEY, filters],
    queryFn: async () => (await api.get<MessStay[]>("/mess", { params: filters })).data,
  });

export function useCreateMessStay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: MessStayCreate) => (await api.post<MessStay>("/mess", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateMessStay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: MessStayUpdate }) =>
      (await api.put<MessStay>(`/mess/${id}`, data)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteMessStay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/mess/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

/** Alias untuk backward compatibility checkout hunian mess (menghapus/menyelesaikan periode hunian). */
export function useCheckoutMessStay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }: { id: string; notes?: string }) => {
      await api.delete(`/mess/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
