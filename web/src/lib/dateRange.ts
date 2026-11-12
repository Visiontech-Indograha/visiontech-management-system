/** Sama dengan `check_date_range` API: tanggal mulai tidak boleh setelah tanggal akhir. Pesan awam, null bila sah. */
export function dateRangeError(from: string, to: string): string | null {
  if (from && to && from > to) return "Tanggal 'Dari' tidak boleh setelah tanggal 'Sampai'.";
  return null;
}
