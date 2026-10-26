import 'package:timezone/data/latest.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

import 'local_notifier.dart';

/// Pengingat absen (docs: aturan jam). Dijadwalkan di HP lewat alarm sistem, jadi tetap bunyi
/// walau aplikasi ditutup; dibatalkan/disusun ulang setiap data absensi dimuat.
///  - belum absen masuk: tiap 5 menit pukul 07:30–08:00 WIB;
///  - sudah masuk, belum pulang: tiap 5 menit dari jam wajib pulang selama 1 jam.
const reminderStep = Duration(minutes: 5);
const _inFrom = Duration(hours: 7, minutes: 30);
const _inTo = Duration(hours: 8);
const _outSpan = Duration(hours: 1);
const _idIn = 7000; // 7000–7099
const _idOut = 7100; // 7100–7199

/// Waktu (UTC) dari [from] sampai [to] tiap [step]; hanya yang masih di depan [now].
List<DateTime> reminderSlots(DateTime from, DateTime to, DateTime now, {Duration step = reminderStep}) {
  final slots = <DateTime>[];
  for (var t = from.toUtc(); !t.isAfter(to.toUtc()); t = t.add(step)) {
    if (t.isAfter(now.toUtc())) slots.add(t);
  }
  return slots;
}

/// Slot pengingat absen masuk untuk tanggal server `yyyy-MM-dd` (jam WIB).
List<DateTime> checkInSlots(String serverToday, DateTime now) {
  final midnightUtc = DateTime.parse('${serverToday}T00:00:00Z').subtract(const Duration(hours: 7));
  return reminderSlots(midnightUtc.add(_inFrom), midnightUtc.add(_inTo), now);
}

/// Slot pengingat absen pulang: dari jam wajib pulang sampai 1 jam sesudahnya.
List<DateTime> checkOutSlots(DateTime requiredOut, DateTime now) =>
    reminderSlots(requiredOut, requiredOut.add(_outSpan), now);

class AttendanceReminders {
  AttendanceReminders(this._notifier);
  final LocalNotifier _notifier;

  static bool _tzReady = false;

  Future<void> sync({
    required String? serverToday,
    required bool checkedIn,
    required bool checkedOut,
    required DateTime? requiredOut,
    DateTime? now,
  }) async {
    if (!_tzReady) {
      tzdata.initializeTimeZones();
      _tzReady = true;
    }
    final clock = now ?? DateTime.now();
    await _notifier.cancelIds([for (var i = 0; i < 200; i++) _idIn + i]);
    if (!checkedIn && serverToday != null) {
      await _schedule(_idIn, checkInSlots(serverToday, clock), 'Belum absen masuk',
          'Batas absen masuk pukul 08:00. Setelah itu tercatat terlambat.');
    } else if (checkedIn && !checkedOut && requiredOut != null) {
      await _schedule(_idOut, checkOutSlots(requiredOut, clock), 'Waktunya absen pulang',
          'Jam kerja 9 jam sudah terpenuhi. Jangan lupa absen pulang.');
    }
  }

  Future<void> _schedule(int baseId, List<DateTime> slots, String title, String body) async {
    final loc = tz.getLocation('Asia/Jakarta');
    for (var i = 0; i < slots.length && i < 100; i++) {
      await _notifier.scheduleAt(baseId + i, tz.TZDateTime.from(slots[i], loc), title, body);
    }
  }
}
