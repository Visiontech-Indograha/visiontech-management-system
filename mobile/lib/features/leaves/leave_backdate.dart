import '../auth/auth_state.dart';

/// Batas cuti mundur: sama dengan `LEAVE_MAX_BACKDATE_DAYS` di API (leave_service.py).
const leaveMaxBackdateDays = 3;

/// Pesan yang sama persis dengan API.
const leaveBackdateMessage =
    'Tanggal mulai cuti paling lambat $leaveMaxBackdateDays hari ke belakang. '
    'Hubungi HR untuk cuti yang lebih lama.';

/// Jam untuk aturan cuti mundur. Uji membekukannya.
DateTime Function() leaveClock = DateTime.now;

/// Peran yang boleh mencatat cuti lebih dari batas mundur (ADMIN_HR_GA, OPERATIONAL_MANAGER, SUPER_ADMIN).
bool leaveBackdateExempt(UserRole role) =>
    role == UserRole.hr || role == UserRole.ops || role == UserRole.superAdmin;

/// Hari ini menurut zona Jakarta (WIB, UTC+7), sebagai tanggal tanpa jam.
DateTime jakartaToday([DateTime? now]) {
  final j = (now ?? leaveClock()).toUtc().add(const Duration(hours: 7));
  return DateTime(j.year, j.month, j.day);
}

/// Tanggal mulai cuti paling awal yang boleh dipilih [role].
DateTime leaveEarliestStart(UserRole role, [DateTime? now]) {
  final today = jakartaToday(now);
  return leaveBackdateExempt(role)
      ? DateTime(today.year, today.month, today.day - 30)
      : DateTime(today.year, today.month, today.day - leaveMaxBackdateDays);
}
