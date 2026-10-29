import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/assets/assets_screen.dart';
import 'package:vms_mobile/features/attendance/recap_screen.dart';

void main() {
  test('label status pengajuan pinjam aset', () {
    expect(loanRequestStatusLabel('PENDING'), 'Menunggu HR/GA');
    expect(loanRequestStatusLabel('APPROVED'), 'Disetujui');
    expect(loanRequestStatusLabel('REJECTED'), 'Ditolak');
    expect(loanRequestStatusLabel('CANCELLED'), 'Dibatalkan');
  });

  test('status pinjaman berjalan', () {
    expect(loanStateLabel({'return_requested_at': null}), 'Sedang dipinjam');
    expect(
      loanStateLabel({'return_requested_at': '2026-10-27T09:00:00Z'}),
      'Menunggu konfirmasi pengembalian',
    );
  });

  test('shiftMonth melewati batas tahun', () {
    expect(shiftMonth('2026-01', -1), '2025-12');
    expect(shiftMonth('2026-12', 1), '2027-01');
    expect(shiftMonth('2026-03', 0), '2026-03');
    expect(shiftMonth('2026-10', -10), '2025-12');
  });
}
