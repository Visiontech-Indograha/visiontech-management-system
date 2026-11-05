import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import { idempotencyHeaders } from "@/lib/idempotency";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
/** Inventaris aset V2 (Milestone 4): alat, kendaraan (+ berkas STNK/BPKB/KIR), peminjaman. */
export type Tool = S["ToolOut"];
export type Vehicle = S["VehicleOut"];
export type Loan = S["LoanOut"];
export type VehicleFile = S["VehicleFileOut"];
export type LoanRequest = S["LoanRequestOut"];
export type AssetAvailability = S["AssetAvailabilityOut"];
export type ToolCreate = S["ToolCreate"];
export type VehicleCreate = S["VehicleCreate"];
export type LoanCreate = S["LoanCreate"];
export type VehicleFileCreate = S["VehicleFileCreate"];
export type AssetKind = "TOOL" | "VEHICLE";
export type ManualStatus = S["AssetStatusUpdate"]["status"];
export type ReturnCondition = NonNullable<S["LoanReturn"]["condition"]>;

const KEY = ["assets"] as const;

export const useTools = () =>
  useQuery({ queryKey: [...KEY, "tools"], queryFn: async () => (await api.get<Tool[]>("/assets/tools")).data });

export const useVehicles = () =>
  useQuery({ queryKey: [...KEY, "vehicles"], queryFn: async () => (await api.get<Vehicle[]>("/assets/vehicles")).data });

/** Peminjaman berjalan (default) atau seluruh riwayat. */
export const useLoans = (open = true) =>
  useQuery({
    queryKey: [...KEY, "loans", { open }],
    queryFn: async () => (await api.get<Loan[]>("/assets/loans", { params: { open } })).data,
  });

/** Ketersediaan alat & kendaraan pada tanggal jadwal (tim pemakai bila dipakai). `team_id` menandai tim peminta. */
export const useAssetAvailability = (date: string, teamId?: string) =>
  useQuery({
    queryKey: [...KEY, "availability", date, teamId ?? null],
    enabled: !!date,
    queryFn: async () =>
      (await api.get<AssetAvailability[]>("/assets/availability", {
        params: { date, ...(teamId ? { team_id: teamId } : {}) },
      })).data,
  });

export const useVehicleFiles = (vehicleId: string) =>
  useQuery({
    queryKey: [...KEY, "vehicle-files", vehicleId],
    queryFn: async () => (await api.get<VehicleFile[]>(`/assets/vehicles/${vehicleId}/files`)).data,
  });

function useAssetMutation<V, D>(fn: (v: V) => Promise<D>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: KEY }) });
}

const path = (kind: AssetKind) => (kind === "TOOL" ? "tools" : "vehicles");

export const useCreateTool = () =>
  useAssetMutation(async (body: ToolCreate) => (await api.post<Tool>("/assets/tools", body)).data);

export const useCreateVehicle = () =>
  useAssetMutation(async (body: VehicleCreate) => (await api.post<Vehicle>("/assets/vehicles", body)).data);

/** Status manual (siap/rusak/hilang/pensiun) — ditolak API bila aset sedang dipinjam. */
export const useSetAssetStatus = () =>
  useAssetMutation(async ({ kind, id, status }: { kind: AssetKind; id: string; status: ManualStatus }) =>
    (await api.post(`/assets/${path(kind)}/${id}/status`, { status })).data);

export const useDeleteAsset = () =>
  useAssetMutation(async ({ kind, id }: { kind: AssetKind; id: string }) =>
    (await api.delete(`/assets/${path(kind)}/${id}`)).data);

export const useAddVehicleFile = (vehicleId: string) =>
  useAssetMutation(async (body: VehicleFileCreate) =>
    (await api.post<VehicleFile[]>(`/assets/vehicles/${vehicleId}/files`, body)).data);

/** Serah terima aset ke karyawan. */
export const useLend = () =>
  useAssetMutation(
    async ({ body, idempotencyKey }: { body: LoanCreate; idempotencyKey?: string }) =>
      (await api.post<Loan>("/assets/loans", body, { headers: idempotencyHeaders(idempotencyKey) })).data,
  );

export const useReturnLoan = () =>
  useAssetMutation(async ({ assignmentId, condition }: { assignmentId: string; condition: ReturnCondition }) =>
    (await api.post<Loan>(`/assets/loans/${assignmentId}/return`, { condition })).data);

/** Pengajuan pinjam dari karyawan (pengelola aset melihat semua). */
export const useLoanRequests = (status?: string) =>
  useQuery({
    queryKey: [...KEY, "loan-requests", { status }],
    queryFn: async () => (await api.get<LoanRequest[]>("/assets/loan-requests", { params: { status } })).data,
  });

/** HR/GA menyetujui (langsung serah terima) atau menolak pengajuan. */
export const useReviewLoanRequest = () =>
  useAssetMutation(async ({ id, decision, note }: { id: string; decision: "APPROVED" | "REJECTED"; note?: string }) =>
    (await api.post<LoanRequest>(`/assets/loan-requests/${id}/review`, { decision, note })).data);
