const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** True bila teks berbentuk UUID — dipakai menjaga parameter URL sebelum memanggil API. */
export function isUuid(value: string | undefined | null): boolean {
  return !!value && UUID_PATTERN.test(value);
}
