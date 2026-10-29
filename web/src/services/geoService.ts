import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type GeoResult = components["schemas"]["GeoResult"];

/** GET /work-plans/geo/search — cari alamat/tempat lewat server (pencarian peta lokasi kerja). */
export async function searchPlaces(q: string): Promise<GeoResult[]> {
  return (await api.get<GeoResult[]>("/work-plans/geo/search", { params: { q } })).data;
}
