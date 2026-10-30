/// Sesi yang ditutup otomatis oleh sistem (lupa absen pulang); keterangan dibuat API saat penutupan otomatis.
bool isAutoClosedSession(Map<String, dynamic> session) {
  final note = session['explanation'];
  // Server menambahkan keterangan ini di belakang catatan lain bila sesi sudah punya catatan (lihat repositori).
  return note is String && note.contains('Lupa absen pulang');
}
