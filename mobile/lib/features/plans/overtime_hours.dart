/// Usulan jam lembur: selisih jam sekarang (WIB) dengan jam pulang jadwal, dibulatkan ke 0,5 jam, maks 12.
/// Null bila bukan jadwal hari ini, jam pulang belum lewat, atau selisih < 0,5 jam.
double? suggestedOvertimeHours({required String workDate, required String clockOutTime, required DateTime nowUtc}) {
  final wib = nowUtc.toUtc().add(const Duration(hours: 7));
  final today = '${wib.year.toString().padLeft(4, '0')}-${wib.month.toString().padLeft(2, '0')}-${wib.day.toString().padLeft(2, '0')}';
  if (workDate != today) return null;
  final parts = clockOutTime.split(':');
  if (parts.length < 2) return null;
  final outMinutes = (int.tryParse(parts[0]) ?? -1) * 60 + (int.tryParse(parts[1]) ?? -1);
  if (outMinutes < 0) return null;
  final extra = wib.hour * 60 + wib.minute - outMinutes;
  if (extra < 30) return null;
  final rounded = (extra / 30).round() / 2;
  return rounded > 12 ? 12 : rounded;
}
