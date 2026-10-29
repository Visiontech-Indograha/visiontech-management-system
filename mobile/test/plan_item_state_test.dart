import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/plans/item_state.dart';

void main() {
  group('itemDisplayState', () {
    test('foto saja (jumlah 0) sudah berarti sedang dikerjakan', () {
      expect(itemDisplayState(raw: 'TODO', done: 0, target: 1, photoCount: 2), 'ITEM_IN_PROGRESS');
    });
    test('jumlah > 0 tanpa foto juga sedang dikerjakan', () {
      expect(itemDisplayState(raw: 'TODO', done: 1, target: 2, photoCount: 0), 'ITEM_IN_PROGRESS');
    });
    test('belum ada foto maupun jumlah tetap belum mulai', () {
      expect(itemDisplayState(raw: 'TODO', done: 0, target: 2, photoCount: 0), 'TODO');
    });
    test('target tercapai selesai', () {
      expect(itemDisplayState(raw: 'TODO', done: 2, target: 2, photoCount: 0), 'DONE');
      expect(itemDisplayState(raw: 'DONE', done: 0, target: 2, photoCount: 0), 'DONE');
    });
    test('status pindah hari tidak tertimpa', () {
      expect(itemDisplayState(raw: 'PENDING_ROLLOVER', done: 1, target: 2, photoCount: 3), 'PENDING_ROLLOVER');
      expect(itemDisplayState(raw: 'SHIFTED_DAY', done: 0, target: 2, photoCount: 1), 'SHIFTED_DAY');
    });
  });

  group('closeDayBlockReason', () {
    test('tanpa laporan memberi alasan', () {
      expect(closeDayBlockReason(hasReport: false, reportPending: false, pendingRollovers: 0),
          'Kirim laporan harian di atas dulu. Setelah terkirim, hari kerja bisa ditutup.');
    });
    test('pindah hari yang menunggu PM lebih dulu', () {
      expect(closeDayBlockReason(hasReport: false, reportPending: false, pendingRollovers: 2),
          startsWith('2 pekerjaan menunggu keputusan PM'));
    });
    test('siap ditutup tidak memberi alasan', () {
      expect(closeDayBlockReason(hasReport: true, reportPending: false, pendingRollovers: 0), isNull);
    });
  });
}
