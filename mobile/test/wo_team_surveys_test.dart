import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:vms_mobile/features/plans/wo_team_surveys_section.dart';

void main() {
  setUpAll(() => initializeDateFormatting('id_ID'));
  testWidgets('kartu survei WO menampilkan WO, klien, site, titik, status', (t) async {
    await t.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: WoSurveyCard(survey: {
          'wo_number': 'WO-001', 'title': 'Pasang CCTV', 'client_name': 'PT Maju',
          'site_name': 'Gudang A', 'survey_date': '2026-11-12',
          'survey_status': 'DRAFT', 'filled_points': 3,
        }),
      ),
    ));
    expect(find.text('WO-001 · Pasang CCTV'), findsOneWidget);
    expect(find.text('PT Maju · Gudang A'), findsOneWidget);
    expect(find.textContaining('3 titik terisi'), findsOneWidget);
    expect(find.text('Sedang diisi'), findsOneWidget);
  });

  test('label status berbahasa awam', () {
    expect(woSurveyStatusLabel['SUBMITTED'], 'Menunggu PM');
  });
}
