import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

const MAX_Q = 100;

/** `page` aman dari URL: bilangan bulat 1..100000, selain itu 1. */
export function parsePage(raw: string | null): number {
  const n = Number(raw);
  return Number.isInteger(n) && n >= 1 && n <= 100000 ? n : 1;
}

/**
 * Kontrol daftar (cari ber-debounce, filter, halaman) yang tersinkron ke URL (?q=&page=&status=…).
 * Nilai dari URL selalu divalidasi: `q` dipotong 100 huruf, `page` dipaksa valid, filter hanya dari daftar `allowed`.
 */
export function useListControls(opts: { size?: number; prefix?: string } = {}) {
  const size = opts.size ?? 20;
  const pre = opts.prefix ?? "";
  const kq = `${pre}q`;
  const kp = `${pre}page`;
  const [params, setParams] = useSearchParams();
  const urlQ = (params.get(kq) ?? "").slice(0, MAX_Q);
  const [input, setInput] = useState(urlQ);
  const search = useDebouncedValue(input.trim(), 300);
  const page = parsePage(params.get(kp));

  const patch = useCallback(
    (changes: Record<string, string | null>, keepPage = false) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(changes)) {
            if (v) next.set(k, v);
            else next.delete(k);
          }
          if (!keepPage) next.delete(kp);
          return next;
        },
        { replace: true },
      );
    },
    [setParams, kp],
  );

  // Kata kunci yang sudah di-debounce masuk URL (mengembalikan halaman ke 1).
  useEffect(() => {
    if (search !== urlQ) patch({ [kq]: search || null });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const filter = (key: string, allowed?: readonly string[]) => {
    const v = params.get(pre + key) ?? "";
    return v && (!allowed || allowed.includes(v)) ? v : "";
  };

  return {
    size,
    page,
    /** Nilai kolom cari (langsung, belum di-debounce). */
    input,
    setInput: (v: string) => setInput(v.slice(0, MAX_Q)),
    /** Kata kunci yang dikirim ke API. */
    search,
    setPage: (p: number) => patch({ [kp]: p > 1 ? String(p) : null }, true),
    filter,
    setFilter: (key: string, value: string) => patch({ [pre + key]: value || null }),
    active: Boolean(search) || [...params.keys()].some((k) => k.startsWith(pre) && k !== kp && k !== kq && params.get(k)),
    reset: () => {
      setInput("");
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const k of [...next.keys()]) if (k.startsWith(pre)) next.delete(k);
          return next;
        },
        { replace: true },
      );
    },
  };
}
