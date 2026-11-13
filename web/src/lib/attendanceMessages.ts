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

/** Catatan menetap di kartu absen saat absen masuk menunggu pemeriksaan (alasan wajah bila ada). */
export function pendingCheckInNote(a: { face_status?: string | null }): string {
  const why = a.face_status === "NOT_ENROLLED" ? "Wajah Anda belum terdaftar, hubungi HR untuk mendaftarkan wajah. " : "";
  return `${why}Absen masuk menunggu pemeriksaan. Absen pulang bisa dilakukan setelah absen masuk disetujui.`;
}
