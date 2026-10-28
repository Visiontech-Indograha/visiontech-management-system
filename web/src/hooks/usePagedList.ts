import { keepPreviousData, useQuery, type UseQueryResult } from "@tanstack/react-query";
import { useListControls } from "@/hooks/useListControls";
import { getPaged, lastPageOf, type Paged } from "@/lib/paged";

export type ListControls = ReturnType<typeof useListControls>;
type Extra = Record<string, string | number | boolean | undefined>;

/**
 * Daftar berhalaman dari API (`q`/`page`/`size` + `X-Total-Count`). `key` memakai awalan kunci layanan yang sama
 * (mis. ["teams"]) sehingga invalidasi setelah ubah/hapus ikut menyegarkan daftar ini.
 */
export function usePagedList<T>(key: readonly unknown[], url: string, controls: ListControls, extra: Extra = {}) {
  const params = { ...extra, q: controls.search || undefined, page: controls.page, size: controls.size };
  return useQuery({
    queryKey: [...key, "page", params],
    queryFn: () => getPaged<T>(url, params),
    placeholderData: keepPreviousData,
  });
}

/** Bentuk tampilan seragam untuk organisme daftar: baris halaman ini, total, halaman terakhir, dan kontrol cari. */
export function pagedView<T>(query: UseQueryResult<Paged<T>>, controls: ListControls) {
  return {
    ...controls,
    rows: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    lastPage: lastPageOf(query.data),
    shownPage: controls.page,
  };
}
