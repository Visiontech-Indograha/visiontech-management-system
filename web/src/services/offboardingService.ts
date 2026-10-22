import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type Offboarding = S["OffboardingListItem"];
export type OffboardingDetail = S["OffboardingDetail"];
export type ClearanceItem = S["ClearanceItemOut"];
export type OffboardingCreate = S["OffboardingCreate"];
export type ClearanceVerify = S["ClearanceItemVerify"];
export type PkwtExpiring = S["PkwtExpiringRow"];

export const REASON_LABEL: Record<string, string> = {
  PKWT_EXPIRED: "PKWT berakhir",
  RESIGN: "Mengundurkan diri",
  TERMINATED: "Diberhentikan",
  RETIRED: "Pensiun",
};
/** docs/35 §7: CLEARANCE_PENDING → SUBMITTED → APPROVED → COMPLETED. */
export const STATUS_LABEL: Record<string, string> = {
  CLEARANCE_PENDING: "Menunggu pengembalian aset",
  SUBMITTED: "Menunggu persetujuan",
  APPROVED: "Disetujui, menunggu tanggal efektif",
  COMPLETED: "Selesai",
};
export const CONDITION_LABEL: Record<string, string> = {
  PENDING: "Belum dikembalikan",
  GOOD: "Baik",
  DAMAGED: "Rusak",
  LOST: "Hilang",
};

const KEY = ["offboardings"] as const;

export const useOffboardings = () =>
  useQuery({ queryKey: KEY, queryFn: async () => (await api.get<Offboarding[]>("/offboarding")).data });

export const useOffboarding = (id: string | null) =>
  useQuery({
    queryKey: [...KEY, id],
    enabled: !!id,
    queryFn: async () => (await api.get<OffboardingDetail>(`/offboarding/${id}`)).data,
  });

export const usePkwtExpiring = (days = 30) =>
  useQuery({
    queryKey: ["pkwt-expiring", days],
    queryFn: async () => (await api.get<PkwtExpiring[]>("/offboarding/pkwt-expiring", { params: { days } })).data,
  });

function useOffboardingMutation<T, R>(fn: (vars: T) => Promise<R>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: KEY });
      await qc.invalidateQueries({ queryKey: ["pkwt-expiring"] });
      await qc.invalidateQueries({ queryKey: ["employees"] });
      await qc.invalidateQueries({ queryKey: ["employee"] });
    },
  });
}

/** HR memulai offboarding; pinjaman aset yang belum kembali otomatis menjadi daftar clearance. */
export const useCreateOffboarding = () =>
  useOffboardingMutation(async (body: OffboardingCreate) =>
    (await api.post<OffboardingDetail>("/offboarding", body)).data);

export const useVerifyClearance = () =>
  useOffboardingMutation(async ({ itemId, body }: { itemId: string; body: ClearanceVerify }) =>
    (await api.post<OffboardingDetail>(`/offboarding/clearance-items/${itemId}/verify`, body)).data);

export const useApproveOffboarding = () =>
  useOffboardingMutation(async ({ id, approval_type }: { id: string; approval_type: "PM" | "HR" }) =>
    (await api.post<OffboardingDetail>(`/offboarding/${id}/approve`, { approval_type })).data);

export const useCancelOffboarding = () =>
  useOffboardingMutation(async ({ id, reason }: { id: string; reason: string }) =>
    (await api.post(`/offboarding/${id}/cancel`, { reason })).data);
