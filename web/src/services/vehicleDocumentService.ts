import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import { getPaged } from "@/lib/paged";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type VehicleDocument = S["VehicleDocumentOut"];
export type VehicleDocumentCreate = S["VehicleDocumentCreate"];
export type VehicleDriver = S["VehicleDriverOut"];
export type DocumentType = S["DocumentTypeOut"];

export const DOC_KEY = ["vehicle-documents"] as const;
/** Batas hari untuk daftar "akan jatuh tempo" dan lencana menu. */
export const EXPIRING_DAYS = 30;

export const useDocumentTypes = () =>
  useQuery({
    queryKey: [...DOC_KEY, "types"],
    queryFn: async () => (await api.get<DocumentType[]>("/vehicle-documents/types")).data,
    staleTime: 5 * 60_000,
  });

/** Jumlah dokumen yang jatuh tempo (termasuk yang sudah lewat), untuk lencana menu. */
export const useExpiringCount = (enabled: boolean) =>
  useQuery({
    queryKey: [...DOC_KEY, "count"],
    enabled,
    queryFn: async () => (await getPaged<VehicleDocument>("/vehicle-documents/expiring", { days: EXPIRING_DAYS, page: 1, size: 1 })).total,
  });

export function useAddVehicleDocument(vehicleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: VehicleDocumentCreate) => (await api.post<VehicleDocument>(`/vehicles/${vehicleId}/documents`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: DOC_KEY }),
  });
}

export const useVehicleDrivers = (vehicleId: string) =>
  useQuery({
    queryKey: [...DOC_KEY, "drivers", vehicleId],
    queryFn: async () => (await api.get<VehicleDriver[]>(`/vehicles/${vehicleId}/drivers`)).data,
  });

export function useAddVehicleDriver(vehicleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (employee_id: string) => (await api.post<VehicleDriver[]>(`/vehicles/${vehicleId}/drivers`, { employee_id })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [...DOC_KEY, "drivers", vehicleId] }),
  });
}

export function useEndVehicleDriver(vehicleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (driverId: string) => (await api.post<VehicleDriver[]>(`/vehicles/${vehicleId}/drivers/${driverId}/end`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [...DOC_KEY, "drivers", vehicleId] }),
  });
}
