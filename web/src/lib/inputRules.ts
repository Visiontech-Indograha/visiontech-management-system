/**
 * Aturan isian bersama untuk formulir web. Batasnya mengikuti API (lihat skema backend):
 * koordinat lintang -90..90 dan bujur -180..180.
 */

/** Nama klien: tolak tag HTML (`<` `>`) dan emoji. Panjang 2..150 mengikuti API. */
const EMOJI = /\p{Extended_Pictographic}/u;
export function namaKlienError(value: string): string | null {
  const v = value.trim();
  if (v.length < 2) return "Nama klien minimal 2 karakter.";
  if (v.length > 150) return "Nama klien maksimal 150 karakter.";
  if (/[<>]/.test(v)) return "Nama klien tidak boleh memuat tanda < atau >.";
  if (EMOJI.test(v)) return "Nama klien tidak boleh memuat emoji.";
  return null;
}

/** Lintang/bujur isian teks. Kosong boleh; kalau diisi harus angka dalam batas. Mengembalikan pesan galat atau null. */
export function koordinatError(lat: string, lng: string): string | null {
  const la = lat.trim();
  const lo = lng.trim();
  if (!la && !lo) return null;
  if (!la || !lo) return "Lintang dan bujur harus diisi berpasangan.";
  const a = Number(la.replace(",", "."));
  const b = Number(lo.replace(",", "."));
  if (!Number.isFinite(a) || Math.abs(a) > 90) return "Lintang tidak valid. Harus antara -90 dan 90.";
  if (!Number.isFinite(b) || Math.abs(b) > 180) return "Bujur tidak valid. Harus antara -180 dan 180.";
  return null;
}

/**
 * Tanggal hasil ketikan manual: `dd/mm/yyyy` (atau `d/m/yyyy`) atau `yyyy-mm-dd`.
 * Mengembalikan `yyyy-mm-dd` bila valid (termasuk tanggal kalender nyata), selain itu null.
 */
export function parseTanggalInput(text: string): string | null {
  const t = text.trim();
  let y: number, m: number, d: number;
  const dmy = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(t);
  const ymd = /^(\d{4})-(\d{2})-(\d{2})$/.exec(t);
  if (dmy) [d, m, y] = [Number(dmy[1]), Number(dmy[2]), Number(dmy[3])];
  else if (ymd) [y, m, d] = [Number(ymd[1]), Number(ymd[2]), Number(ymd[3])];
  else return null;
  const dt = new Date(Date.UTC(y, m - 1, d));
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return null;
  return `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}
