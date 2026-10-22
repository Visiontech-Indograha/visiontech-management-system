import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";

export interface MessStay {
  id: string;
  employee_id: string;
  employee_name?: string;
  mess_name: string;
  room_number?: string;
  check_in_date: string;
  check_out_date?: string;
  status: "ACTIVE" | "CHECKED_OUT";
  notes?: string;
}

export interface MessStayCreate {
  employee_id: string;
  mess_name: string;
  room_number?: string;
  check_in_date: string;
  notes?: string;
}

const KEY = ["mess-stays"] as const;

export const useMessStays = () =>
  useQuery({
    queryKey: KEY,
    queryFn: async () => (await api.get<MessStay[]>("/mess")).data,
  });

export function useCreateMessStay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: MessStayCreate) => (await api.post<MessStay>("/mess", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useCheckoutMessStay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, notes }: { id: string; notes?: string }) => {
      await api.post(`/mess/${id}/checkout`, { notes });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
