import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
/** Aset + alokasi berjalan + pengajuan pengembalian yang menunggu (GET /assets, R-19). */
export type Asset = S["AssetListItem"];
export type AssetCreate = S["AssetCreate"];
type WorkPlan = S["WorkPlanResponse"];

const KEY = ["assets"] as const;

export const useAssets = () => useQuery({ queryKey: KEY, queryFn: async () => (await api.get<Asset[]>("/assets")).data });

/** SK aktif yang terlihat pengguna, untuk pilihan alokasi / pelepasan. */
const ACTIVE = ["PUBLISHED", "ACCEPTED", "IN_PROGRESS"];
export const useActivePlans = () =>
  useQuery({
    queryKey: ["work-plans", { status: "", archived: false }],
    queryFn: async () => (await api.get<WorkPlan[]>("/work-plans", { params: { archived: false } })).data,
    select: (plans) => plans.filter((p) => ACTIVE.includes(p.status)),
  });

function useAssetMutation<V, D>(fn: (v: V) => Promise<D>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => qc.invalidateQueries({ queryKey: KEY }) });
}

export const useCreateAsset = () =>
  useAssetMutation(async (body: AssetCreate) => (await api.post<Asset>("/assets", body)).data);

export const useReserveAsset = () =>
  useAssetMutation(async ({ id, ...body }: { id: string } & S["AssetReserveRequest"]) =>
    (await api.post<S["AssetAllocationResponse"]>(`/assets/${id}/reserve`, body)).data,
  );

export const useReleaseAsset = () =>
  useAssetMutation(async ({ id, ...body }: { id: string } & S["AssetReleaseRequest"]) =>
    (await api.post<S["AssetStatusResponse"]>(`/assets/${id}/release`, body)).data,
  );

/** Ketua SK peminjam mengajukan pengembalian (domain.js RETURN_ASSET). */
export const useRequestReturn = () =>
  useAssetMutation(async ({ allocation_id, ...body }: { allocation_id: string } & S["AssetReturnCreate"]) =>
    (await api.post<S["AssetReturnResponse"]>(`/assets/allocations/${allocation_id}/return`, body)).data,
  );

/** Petugas aset memeriksa pengembalian: terima (aset tersedia lagi) / tolak (kembali ke tim) — VERIFY_RETURN. */
export const useVerifyReturn = () =>
  useAssetMutation(async ({ return_id, ...body }: { return_id: string } & S["AssetReturnVerify"]) =>
    (await api.post<S["AssetReturnResponse"]>(`/assets/returns/${return_id}/verify`, body)).data,
  );

export type AssetReturnItem = S["AssetReturnHistoryItem"];

/** Riwayat pengembalian aset (GET /assets/{id}/returns) — dasar BAST. */
export const useAssetReturns = (assetId: string) =>
  useQuery({
    queryKey: [...KEY, assetId, "returns"],
    queryFn: async () => (await api.get<AssetReturnItem[]>(`/assets/${assetId}/returns`)).data,
  });

export const useCheckAsset = () =>
  useAssetMutation(async ({ id, ...body }: { id: string } & S["AssetCheckRequest"]) =>
    (await api.post<S["AssetStatusResponse"]>(`/assets/${id}/check`, body)).data,
  );
