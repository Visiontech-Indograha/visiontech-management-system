import type { SyntheticEvent } from "react";

type Ctl = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

function fmt(v: string, type: string): string {
  if (type === "date" && /^\d{4}-\d{2}-\d{2}$/.test(v)) {
    const [y, m, d] = v.split("-");
    return `${d}-${m}-${y}`;
  }
  return v;
}

/** Pesan Indonesia awam untuk keadaan `validity` bawaan browser; null bila valid. */
export function indonesianValidityMessage(el: Ctl): string | null {
  const v = el.validity;
  if (v.valid) return null;
  const type = el instanceof HTMLInputElement ? el.type : "";
  const min = el instanceof HTMLInputElement ? el.min : "";
  const max = el instanceof HTMLInputElement ? el.max : "";
  if (v.valueMissing) return type === "checkbox" ? "Centang kotak ini dulu." : "Isian ini wajib diisi.";
  if (v.rangeUnderflow) {
    return type === "date" ? `Tanggal tidak boleh sebelum ${fmt(min, type)}.` : `Nilai minimal ${min}.`;
  }
  if (v.rangeOverflow) {
    return type === "date" ? `Tanggal tidak boleh setelah ${fmt(max, type)}.` : `Nilai maksimal ${max}.`;
  }
  if (v.badInput) return type === "date" ? "Isi tanggal yang benar." : "Isi dengan angka yang benar.";
  if (v.stepMismatch) return "Isi dengan angka yang sesuai.";
  if (v.tooShort) return `Minimal ${(el as HTMLInputElement).minLength} karakter.`;
  if (v.tooLong) return `Maksimal ${(el as HTMLInputElement).maxLength} karakter.`;
  if (v.typeMismatch || v.patternMismatch) return "Format isian belum sesuai.";
  return "Isian belum benar.";
}

/** Handler `onInvalid`: ganti pesan bawaan browser (Inggris) dengan pesan Indonesia. */
export function handleInvalid(e: SyntheticEvent<Ctl>): void {
  const el = e.currentTarget;
  el.setCustomValidity("");
  const msg = indonesianValidityMessage(el);
  if (msg) el.setCustomValidity(msg);
}

/** Handler `onInput`/`onChange`: hapus pesan khusus agar validasi dihitung ulang. */
export function clearCustomValidity(e: SyntheticEvent<Ctl>): void {
  e.currentTarget.setCustomValidity("");
}
