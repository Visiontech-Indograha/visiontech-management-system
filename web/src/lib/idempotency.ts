import { useCallback, useState } from "react";

/** Nama header yang dibaca API untuk mencegah pengajuan ganda. */
export const IDEMPOTENCY_HEADER = "Idempotency-Key";

export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

/** Header untuk satu pengajuan; kosong bila kunci tidak ada. */
export function idempotencyHeaders(key?: string): Record<string, string> | undefined {
  return key ? { [IDEMPOTENCY_HEADER]: key } : undefined;
}

/**
 * Kunci per niat pengajuan: dibuat sekali, dipakai ulang saat coba lagi atau klik ganda,
 * diganti saat isi form (`signature`) berubah atau setelah `renew()` (sukses).
 * `keyFor(suffix)` menurunkan kunci stabil untuk beberapa permintaan dalam satu niat.
 */
export function useIdempotencyKey(signature: string) {
  const [state, setState] = useState(() => ({ signature, key: newIdempotencyKey() }));
  let key = state.key;
  if (state.signature !== signature) {
    // Isi form berubah: niat baru, kunci baru (pola turunan state saat render).
    key = newIdempotencyKey();
    setState({ signature, key });
  }
  const renew = useCallback(() => {
    setState((s) => ({ signature: s.signature, key: newIdempotencyKey() }));
  }, []);
  const keyFor = (suffix?: string | number) => (suffix === undefined ? key : `${key}:${suffix}`);
  return { key, keyFor, renew };
}
