import { useEffect, useRef } from "react";

/** Kolom penjelasan wajib: bila kirim gagal karena kosong, tampilkan galat di kolom dan pindahkan fokus ke sana. */
export function useRequiredExplanation(asked: boolean, failed: boolean, value: string) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const error = asked && failed && !value.trim() ? "Penjelasan wajib diisi." : undefined;
  useEffect(() => {
    if (error) ref.current?.focus();
  }, [error]);
  return { ref, error };
}
