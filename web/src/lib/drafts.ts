import { useEffect } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { create } from "zustand";

/**
 * Regresi R5 (dok 07 §3): teks laporan yang belum disimpan tidak boleh hilang saat pengguna
 * berpindah layar lalu kembali. Draf = state klien (Zustand), bukan data server — dibuang setelah
 * tersimpan ke API.
 */
type DraftStore = {
  drafts: Record<string, FieldValues>;
  put: (key: string, values: FieldValues) => void;
  drop: (key: string) => void;
};

export const useDrafts = create<DraftStore>((set) => ({
  drafts: {},
  put: (key, values) => set((s) => ({ drafts: { ...s.drafts, [key]: values } })),
  drop: (key) =>
    set((s) => {
      const drafts = { ...s.drafts };
      delete drafts[key];
      return { drafts };
    }),
}));

/** Pulihkan draf `key` ke formulir saat dipasang, simpan setiap ketikan. → fungsi untuk membuang draf. */
export function useFormDraft<T extends FieldValues>(key: string, form: UseFormReturn<T>): () => void {
  useEffect(() => {
    const saved = useDrafts.getState().drafts[key] as T | undefined;
    if (saved) form.reset(saved, { keepDefaultValues: true });
    const sub = form.watch((values) => useDrafts.getState().put(key, values as FieldValues));
    return () => sub.unsubscribe();
  }, [key, form]);
  return () => useDrafts.getState().drop(key);
}
