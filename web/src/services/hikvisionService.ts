import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type Perangkat = S["PerangkatOut"];
export type PerangkatBuat = S["PerangkatBuat"];
export type PerangkatUbah = S["PerangkatUbah"];
export type TokenBaru = S["TokenBaru"];
export type StatusPerangkat = S["StatusPerangkat"];
export type Pemetaan = S["PemetaanOut"];
export type UsulanPemetaan = S["UsulanPemetaan"];
export type PemetaanOtomatis = S["PemetaanOtomatisOut"];
export type PemetaanDiterapkan = S["PemetaanDiterapkan"];
export type BandingBaris = S["BandingBaris"];
export type BandingBayangan = S["BandingBayangan"];

const KEY = ["hikvision"] as const;

/** Batas `size` API (MAX_PAGE_SIZE di api/app/core/list_params.py). Lebih dari ini ditolak 422. */
export const BATAS_UKURAN_HALAMAN = 100;
const BATAS_HALAMAN = 50;

/** Ambil semua baris sebuah daftar dengan paginasi sah (size <= batas API), berhenti saat halaman tak penuh. */
export async function ambilSemuaHalaman<T>(url: string): Promise<T[]> {
  const hasil: T[] = [];
  for (let page = 1; page <= BATAS_HALAMAN; page += 1) {
    const res = await api.get<T[]>(url, { params: { page, size: BATAS_UKURAN_HALAMAN } });
    hasil.push(...res.data);
    const total = Number(res.headers?.["x-total-count"]);
    if (res.data.length < BATAS_UKURAN_HALAMAN || (Number.isFinite(total) && hasil.length >= total)) break;
  }
  return hasil;
}
const dev = (id: string) => `/hikvision/devices/${id}`;

/** GET /hikvision/devices/{id}/bayangan: tap mesin vs absen aplikasi per karyawan-hari (baca saja, maks 31 hari). */
export interface BandingFilter {
  status?: BandingBaris["status"];
  q?: string;
  page: number;
  size: number;
}

/** Filter status, cari awalan nama, dan halaman dikerjakan server; total dari X-Total-Count (cadangan: total_baris). */
export const useBandingBayangan = (id: string, dari: string, sampai: string, f: BandingFilter) => {
  const params = { dari, sampai, status: f.status || undefined, q: f.q || undefined, page: f.page, size: f.size };
  return useQuery({
    queryKey: [...KEY, "bayangan", id, params],
    enabled: Boolean(id && dari && sampai),
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const res = await api.get<BandingBayangan>(`${dev(id)}/bayangan`, { params });
      const header = Number(res.headers?.["x-total-count"]);
      const total = Number.isFinite(header) && header >= 0 ? header : (res.data.total_baris ?? res.data.items.length);
      return { ...res.data, total_baris: total };
    },
  });
};

/** GET /hikvision/devices (izin manage:hikvision). */
export const useHikvisionDevices = () =>
  useQuery({
    queryKey: [...KEY, "devices"],
    queryFn: () => ambilSemuaHalaman<Perangkat>("/hikvision/devices"),
  });

export const useDeviceStatus = (id: string) =>
  useQuery({
    queryKey: [...KEY, "status", id],
    queryFn: async () => (await api.get<StatusPerangkat>(`${dev(id)}/status`)).data,
  });

/** POST /hikvision/devices: respons memuat `penerima` (tautan tampil sekali). */
export function useCreateDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PerangkatBuat) =>
      (await api.post<{ perangkat: Perangkat; penerima: TokenBaru }>("/hikvision/devices", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateDevice(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PerangkatUbah) => (await api.patch<Perangkat>(dev(id), body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(dev(id));
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

/** POST /hikvision/devices/{id}/token: tautan lama tidak berlaku lagi. */
export const useRenewReceiver = () =>
  useMutation({ mutationFn: async (id: string) => (await api.post<TokenBaru>(`${dev(id)}/token`)).data });

export const useMappings = (id: string) =>
  useQuery({
    queryKey: [...KEY, "mappings", id],
    queryFn: () => ambilSemuaHalaman<Pemetaan>(`${dev(id)}/mappings`),
  });

export const useMappingSuggestions = (id: string, enabled: boolean) =>
  useQuery({
    queryKey: [...KEY, "suggestions", id],
    enabled,
    queryFn: async () => (await api.get<UsulanPemetaan>(`${dev(id)}/mappings/suggestions`)).data,
  });

export function useSaveMapping(deviceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (a: { mapId?: string; employee_id: string; employee_no_string: string }) => {
      if (a.mapId) await api.patch(`${dev(deviceId)}/mappings/${a.mapId}`, { employee_id: a.employee_id });
      else await api.post(`${dev(deviceId)}/mappings`, { employee_no_string: a.employee_no_string, employee_id: a.employee_id });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteMapping(deviceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (mapId: string) => {
      await api.delete(`${dev(deviceId)}/mappings/${mapId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useAutoMap(deviceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post<PemetaanOtomatis>(`${dev(deviceId)}/mappings/auto`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useApplyMappings(deviceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post<PemetaanDiterapkan>(`${dev(deviceId)}/mappings/apply`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
