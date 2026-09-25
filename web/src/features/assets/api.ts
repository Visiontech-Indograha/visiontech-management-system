import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";

type S = components["schemas"];
export type Asset = S["AssetResponse"];
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

export const useCheckAsset = () =>
  useAssetMutation(async ({ id, ...body }: { id: string } & S["AssetCheckRequest"]) =>
    (await api.post<S["AssetStatusResponse"]>(`/assets/${id}/check`, body)).data,
  );
