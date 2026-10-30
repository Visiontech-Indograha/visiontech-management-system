/** Batas volume target pekerjaan; sama dengan skema API (plan_item_schema: gt=0, le=99999999). */
export const TARGET_QTY_MAX = 99_999_999;

export type QtyResult = { ok: true; value: string } | { ok: false; message: string };

/**
 * Volume target: koma diterima sebagai desimal (1,5 → 1.5), paling banyak 2 angka di belakang koma,
 * lebih dari 0 dan tidak melebihi batas API. Pesan berbahasa Indonesia untuk kolom itu sendiri.
 */
export function parseTargetQty(raw: string): QtyResult {
  const s = raw.trim().replace(",", ".");
  if (!s) return { ok: false, message: "Target volume wajib diisi." };
  if (!/^\d+(\.\d+)?$/.test(s)) return { ok: false, message: "Target volume hanya boleh angka." };
  const [, frac = ""] = s.split(".");
  if (frac.length > 2) return { ok: false, message: "Target volume maksimal 2 angka di belakang koma." };
  const n = Number(s);
  if (n <= 0) return { ok: false, message: "Target volume harus lebih dari 0." };
  if (n > TARGET_QTY_MAX) return { ok: false, message: "Target volume maksimal 99.999.999." };
  return { ok: true, value: s };
}
