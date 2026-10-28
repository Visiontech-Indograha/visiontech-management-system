import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/shared/ui/vms_list_filter.dart';

void main() {
  final items = [
    for (var i = 0; i < 45; i++) {'name': i == 7 ? 'Cuti Tahunan' : 'Item $i', 'status': i.isEven ? 'A' : 'B'},
  ];

  test('cari tanpa beda huruf besar dan potong halaman 20', () {
    final q = ListQuery();
    expect(q.visible(q.filter(items, (e) => [e['name']])).length, 20);
    q.setQuery('CUTI');
    final hit = q.filter(items, (e) => [e['name']]);
    expect(hit.length, 1);
    q.setQuery('tidak-ada');
    expect(q.filter(items, (e) => [e['name']]), isEmpty);
  });

  test('chip menyaring dan muat lebih banyak menambah 20', () {
    final q = ListQuery()..setChip('A');
    final all = q.filter(items, (e) => [e['name']], chipTest: (e, chip) => e['status'] == chip);
    expect(all.length, 23);
    expect(q.visible(all).length, 20);
    q.loadMore();
    expect(q.visible(all).length, 23);
    q.reset();
    expect(q.active, isFalse);
    expect(q.shown, 20);
  });
}
