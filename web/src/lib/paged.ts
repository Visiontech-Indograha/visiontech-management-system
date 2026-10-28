import { api } from "@/lib/apiClient";

/** Hasil daftar berhalaman dari API (`X-Total-Count` = jumlah setelah filter, sebelum dipotong halaman). */
export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

/** Ambil daftar dengan `q`/`page`/`size`; tanpa header total (server lama) total = jumlah baris yang diterima. */
export async function getPaged<T>(
  url: string,
  params: Record<string, string | number | undefined>,
): Promise<Paged<T>> {
  const res = await api.get<T[]>(url, { params });
  const header = Number(res.headers?.["x-total-count"]);
  return {
    items: res.data,
    total: Number.isFinite(header) && header >= 0 ? header : res.data.length,
    page: Number(params.page) || 1,
    size: Number(params.size) || res.data.length,
  };
}

export const lastPageOf = (p: { total: number; size: number } | undefined) =>
  p && p.size > 0 ? Math.max(1, Math.ceil(p.total / p.size)) : 1;
