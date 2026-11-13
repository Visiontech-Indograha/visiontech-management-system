/** Alasan absen web "perlu ditinjau" dalam bahasa awam, dengan satu langkah perbaikan bila ada. */
export interface ReviewReasonInfo {
  text: string;
  /** "ENROLL" = tombol ke halaman Daftar wajah. */
  action?: "ENROLL";
}

const REASONS: Record<string, ReviewReasonInfo> = {
  FACE_NOT_ENROLLED: { text: "Wajah Anda belum terdaftar. Daftarkan wajah dulu.", action: "ENROLL" },
  FACE_MISMATCH: { text: "Wajah kurang cocok. Coba lagi di tempat lebih terang, hadap kamera." },
  FACE_UNAVAILABLE: { text: "Wajah belum bisa diperiksa saat ini. Absen Anda dicatat dan ditinjau HR." },
  LOKASI_DI_LUAR_ZONA: { text: "Anda berada di luar area kantor. Absen Anda dicatat dan ditinjau HR." },
  LOKASI_KASAR: { text: "Lokasi tidak akurat (laptop tanpa GPS). Absen Anda dicatat dan ditinjau HR kantor tugas." },
};

/** Kode tak dikenal tetap diberi kalimat awam (tanpa menampilkan kode mentah). */
export function reviewReasonInfo(code: string): ReviewReasonInfo {
  return REASONS[code] ?? { text: "Absen Anda perlu ditinjau HR." };
}

export function reviewReasonTexts(codes: readonly string[] | null | undefined): string[] {
  return [...new Set((codes ?? []).map((c) => reviewReasonInfo(c).text))];
}

export function accuracyText(m: number | null | undefined): string | null {
  return m == null ? null : `Akurasi lokasi ±${Math.round(m)} m`;
}
