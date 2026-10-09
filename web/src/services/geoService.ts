import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type GeoResult = components["schemas"]["GeoResult"];

/** GET /geo/search — cari alamat/tempat lewat server (pencarian peta lokasi kerja). */
export async function searchPlaces(q: string): Promise<GeoResult[]> {
  return (await api.get<GeoResult[]>("/geo/search", { params: { q } })).data;
}
