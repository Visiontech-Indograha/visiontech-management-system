/// Sesi yang ditutup otomatis oleh sistem (lupa absen pulang); keterangan dibuat API saat penutupan otomatis.
bool isAutoClosedSession(Map<String, dynamic> session) {
  final note = session['explanation'];
  return note is String && note.startsWith('Lupa absen pulang');
}
