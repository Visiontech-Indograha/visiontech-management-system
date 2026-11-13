/** Pesan awam setelah absen masuk web; alasan "perlu ditinjau" diambil dari data API, bukan ditebak dari jarak. */
export function checkInMessage(
  a: { status: string; face_status?: string | null },
  distanceText: string,
): string {
  if (a.status !== "NEEDS_REVIEW") return "Absen masuk tercatat.";
  if (a.face_status === "NOT_ENROLLED") {
    return "Absen masuk tercatat, tetapi wajah Anda belum terdaftar. Hubungi HR untuk mendaftarkan wajah.";
  }
  return `Absen masuk tercatat (${distanceText} dari lokasi) dan menunggu ditinjau.`;
}
