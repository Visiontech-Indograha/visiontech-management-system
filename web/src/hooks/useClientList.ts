import { useMemo } from "react";
import { useListControls } from "@/hooks/useListControls";

const fold = (v: unknown) =>
  String(v ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();

/**
 * Cari + halaman untuk daftar kecil yang sudah dimuat penuh (Tim, Mess, Offboarding, Aset): tersinkron ke URL,
 * tanpa huruf besar/aksen. `prefix` memisahkan beberapa daftar di satu halaman.
 */
export function useClientList<T>(
  items: readonly T[] | undefined,
  haystack: (item: T) => readonly unknown[],
  opts: { prefix?: string; size?: number; extra?: (item: T) => boolean } = {},
) {
  const controls = useListControls({ size: opts.size ?? 20, prefix: opts.prefix });
  const { search, page, size } = controls;
  const filtered = useMemo(() => {
    const needle = fold(search);
    return (items ?? []).filter(
      (it) => (!opts.extra || opts.extra(it)) && (!needle || haystack(it).some((v) => fold(v).includes(needle))),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, search, opts.extra]);
  const lastPage = Math.max(1, Math.ceil(filtered.length / size));
  const shownPage = Math.min(page, lastPage);
  const rows = filtered.slice((shownPage - 1) * size, shownPage * size);
  return { ...controls, rows, total: filtered.length, lastPage, shownPage, loaded: items?.length ?? 0 };
}
