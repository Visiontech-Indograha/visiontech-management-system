import { useState } from "react";
import { keepPreviousData, useInfiniteQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/apiClient";

type Params = Record<string, string | number | boolean | undefined>;

export const CURSOR_NOTICE = "Daftar sudah berubah, jadi dimuat ulang dari awal.";

/** Satu halaman keyset: isi respons + kursor halaman berikutnya (header `X-Next-Cursor`; tidak ada = halaman terakhir). */
export interface KeysetPage<B> {
  body: B;
  next: string | null;
}

/** Status "Muat lebih banyak" untuk organisme daftar. Sengaja tanpa total (mode keyset tidak menghitung). */
export interface KeysetMore {
  hasMore: boolean;
  loading: boolean;
  notice: string | null;
  onLoadMore: () => void;
}

/** GET satu halaman keyset. `cursor` kosong ("") = halaman pertama (tetap dikirim agar server masuk mode keyset). */
export async function getKeysetPage<B>(url: string, params: Params, cursor: string): Promise<KeysetPage<B>> {
  const res = await api.get<B>(url, { params: { ...params, cursor } });
  const next = res.headers?.["x-next-cursor"];
  return { body: res.data, next: typeof next === "string" && next ? next : null };
}

/**
 * Daftar keyset dengan TanStack Query. `merge` menggabungkan semua halaman jadi satu bentuk yang sama dengan daftar lama,
 * sehingga organisme tetap memakai `query.data`. Kursor tak valid (422) -> daftar dimulai ulang dari halaman pertama.
 */
export function useKeysetList<B, D>({ key, url, params, merge }: {
  key: readonly unknown[];
  url: string;
  params: Params;
  merge: (pages: B[]) => D;
}) {
  const qc = useQueryClient();
  const fullKey = [...key, "keyset", params];
  const [noticeKey, setNoticeKey] = useState<string | null>(null);
  const q = useInfiniteQuery({
    queryKey: fullKey,
    initialPageParam: "",
    queryFn: ({ pageParam }) => getKeysetPage<B>(url, params, pageParam),
    getNextPageParam: (last) => last.next ?? undefined,
    placeholderData: keepPreviousData,
  });
  const id = JSON.stringify(fullKey);

  const onLoadMore = async () => {
    const r = await q.fetchNextPage();
    if (r.isError && r.error instanceof ApiError && r.error.status === 422) {
      setNoticeKey(id);
      await qc.resetQueries({ queryKey: fullKey });
    }
  };

  const data = q.data ? merge(q.data.pages.map((p) => p.body)) : undefined;
  const query = { ...q, data } as unknown as UseQueryResult<D>;
  const more: KeysetMore = {
    hasMore: Boolean(q.hasNextPage),
    loading: q.isFetchingNextPage,
    notice: noticeKey === id ? CURSOR_NOTICE : null,
    onLoadMore: () => void onLoadMore(),
  };
  return { query, more };
}
