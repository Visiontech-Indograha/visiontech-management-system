import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/shared/ui/vms_ui.dart';

void main() {
  group('jadwalTitle', () {
    test('lokasi lebih dulu, lalu nama proyek', () {
      expect(jadwalTitle({'site_name': 'Gardu A', 'project_title': 'Proyek X'}), 'Gardu A');
      expect(jadwalTitle({'site_name': '  ', 'project_title': 'Proyek X'}), 'Proyek X');
    });
    test('tanpa lokasi dan proyek: nama tim dan tanggal kerja, bukan "Tanpa judul"', () {
      final title = jadwalTitle({'site_name': null, 'project_title': '', 'team_name': 'Alfa', 'work_date': '2026-10-30'});
      expect(title, 'Tim Alfa · 30 Okt');
      expect(title, isNot(contains('Tanpa judul')));
    });
    test('hanya tanggal atau hanya tim tetap menampilkan yang ada', () {
      expect(jadwalTitle({'work_date': '2026-03-05'}), '5 Mar');
      expect(jadwalTitle({'team_name': 'Bravo'}), 'Tim Bravo');
      expect(jadwalTitle({}), 'Jadwal tanpa lokasi');
    });
  });
}
