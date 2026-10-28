import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";

export type MessStatus = "REQUESTED" | "APPROVED" | "REJECTED" | "CANCELLED";

export const MESS_STATUS_LABEL: Record<MessStatus, string> = {
  REQUESTED: "Menunggu persetujuan",
  APPROVED: "Disetujui",
  REJECTED: "Ditolak",
  CANCELLED: "Dibatalkan",
};

export interface MessStay {
  mess_stay_id: string;
  mess_id?: string | null;
  mess_name: string;
  city: string;
  address: string;
  latitude?: number | null;
  longitude?: number | null;
  employee_id: string;
  employee_name?: string | null;
  employee_photo_file_id?: string | null;
  employee_no?: string | null;
  stay_start_date: string;
  stay_end_date: string;
  status: MessStatus;
  request_note?: string | null;
  decision_note?: string | null;
  decided_at?: string | null;
  create_at?: string;
}

export interface MessPlace {
  mess_id: string;
  mess_name: string;
  city: string;
  address: string;
  latitude?: number | null;
  longitude?: number | null;
  capacity?: number | null;
  occupied: number;
}

export interface MessPlaceInput {
  mess_name: string;
  city: string;
  address: string;
  latitude?: number | null;
  longitude?: number | null;
  capacity?: number | null;
}

export interface MessStayCreate {
  employee_id: string;
  mess_id: string;
  stay_start_date: string;
  stay_end_date: string;
}

const KEY = ["mess-stays"] as const;
const PLACES = ["mess-places"] as const;

export const useMessStays = (filters?: {
  employee_id?: string;
  start?: string;
  end?: string;
  status?: MessStatus;
}) =>
  useQuery({
    queryKey: [...KEY, filters],
    queryFn: async () =>
      (await api.get<MessStay[]>("/mess", { params: filters })).data,
  });

export const useMessPlaces = () =>
  useQuery({
    queryKey: PLACES,
    queryFn: async () => (await api.get<MessPlace[]>("/mess/places")).data,
  });

function useInvalidate() {
  const qc = useQueryClient();
  return () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: KEY }),
      qc.invalidateQueries({ queryKey: PLACES }),
    ]);
}

export function useCreateMessStay() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async (body: MessStayCreate) =>
      (await api.post<MessStay>("/mess", body)).data,
    onSuccess: done,
  });
}

export function useDecideMessStay() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async ({
      id,
      approve,
      note,
    }: {
      id: string;
      approve: boolean;
      note?: string;
    }) =>
      (
        await api.post<MessStay>(`/mess/${id}/decision`, {
          approve,
          note: note || null,
        })
      ).data,
    onSuccess: done,
  });
}

/** Selesai inap: periode dimajukan ke hari ini, riwayat tetap tersimpan. */
export function useCheckoutMessStay() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async ({ id }: { id: string }) =>
      (await api.post<MessStay>(`/mess/${id}/end`)).data,
    onSuccess: done,
  });
}

export function useCreateMessPlace() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async (body: MessPlaceInput) =>
      (await api.post<MessPlace>("/mess/places", body)).data,
    onSuccess: done,
  });
}

export function useUpdateMessPlace() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: MessPlaceInput }) =>
      (await api.put<MessPlace>(`/mess/places/${id}`, data)).data,
    onSuccess: done,
  });
}

export function useDeleteMessPlace() {
  const done = useInvalidate();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/mess/places/${id}`);
    },
    onSuccess: done,
  });
}
