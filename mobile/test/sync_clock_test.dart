import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/data/sync_engine.dart';

import 'support/fake_backend.dart';

/// Golden sinkron tidak boleh bergantung pada tanggal hari ini: SyncEngine memakai jam yang disuntikkan.
void main() {
  test('submit mencatat client_created_at dari jam suntikan, bukan jam sistem', () async {
    final db = memoryDb();
    addTearDown(db.close);
    final engine = engineWith(db, FakeBackend(), clock: () => DateTime.utc(2026, 10, 2, 3));
    await engine.submit(OfflineOp.taskToggle, {'task_id': 't1'});
    final rows = await db.select(db.pendingSyncOperations).get();
    expect(rows.single.payloadJson, contains('"client_created_at":"2026-10-02T03:00:00.000Z"'));
  });
}
