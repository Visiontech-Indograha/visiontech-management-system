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
    test('hari yang sudah ditutup: item parsial berlabel Belum selesai, bukan Sedang dikerjakan', () {
      expect(itemDisplayState(raw: 'TODO', done: 2, target: 5, photoCount: 0, dayStatus: 'COMPLETED'), 'ITEM_PARTIAL');
      expect(itemDisplayState(raw: 'TODO', done: 0, target: 5, photoCount: 1, dayStatus: 'COMPLETED'), 'ITEM_PARTIAL');
      expect(itemDisplayState(raw: 'TODO', done: 2, target: 5, photoCount: 0, dayStatus: 'ONGOING'), 'ITEM_IN_PROGRESS');
      expect(itemDisplayState(raw: 'TODO', done: 5, target: 5, photoCount: 0, dayStatus: 'COMPLETED'), 'DONE');
    });
    test('status pindah hari dan dibatalkan tidak tertimpa', () {
      expect(itemDisplayState(raw: 'PENDING_ROLLOVER', done: 1, target: 2, photoCount: 3), 'PENDING_ROLLOVER');
      expect(itemDisplayState(raw: 'SHIFTED_DAY', done: 0, target: 2, photoCount: 1), 'SHIFTED_DAY');
      expect(itemDisplayState(raw: 'CANCELLED', done: 1, target: 2, photoCount: 2, dayStatus: 'COMPLETED'), 'CANCELLED');
    });
  });

  group('closeDayBlockReason', () {
    test('tanpa laporan memberi alasan', () {
      expect(closeDayBlockReason(hasReport: false, reportPending: false, pendingRollovers: 0),
          'Kirim laporan harian di atas dulu. Setelah terkirim, hari kerja bisa ditutup.');
    });
    test('masih ada item belum selesai menahan penutupan hari', () {
      expect(
        closeDayBlockReason(hasReport: true, reportPending: false, pendingRollovers: 0, unfinishedItems: 1),
        'Masih ada pekerjaan belum selesai. Selesaikan atau ajukan pindah hari dulu, atau minta atasan menutup hari kerja.',
      );
    });
    test('pindah hari yang menunggu PM dijelaskan spanduk, tidak diulang sebagai alasan', () {
      expect(closeDayBlockReason(hasReport: false, reportPending: false, pendingRollovers: 2), isNull);
    });
    test('siap ditutup tidak memberi alasan', () {
      expect(closeDayBlockReason(hasReport: true, reportPending: false, pendingRollovers: 0), isNull);
    });
  });
}
