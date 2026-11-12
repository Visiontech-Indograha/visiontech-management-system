import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/shared/app_frame.dart';

Widget _host({bool beta = false, bool dev = false}) => Directionality(
  textDirection: TextDirection.ltr,
  child: Builder(
    builder: (c) => vmsAppFrame(c, const SizedBox(), beta: beta, dev: dev),
  ),
);

void main() {
  testWidgets('tanpa define: tidak ada pita', (t) async {
    await t.pumpWidget(_host());
    expect(find.byType(Banner), findsNothing);
  });
  testWidgets('VMS_BETA: pita BETA', (t) async {
    await t.pumpWidget(_host(beta: true));
    expect(t.widget<Banner>(find.byType(Banner)).message, 'BETA · uji lokal');
  });
  testWidgets('VMS_DEVELOPMENT: pita DEV, warna beda', (t) async {
    await t.pumpWidget(_host(dev: true));
    final b = t.widget<Banner>(find.byType(Banner));
    expect(b.message, 'DEV · uji lokal');
    expect(b.color, vmsDevBannerColor);
    expect(vmsDevBannerColor.computeLuminance() < 0.1, isTrue);
  });
  testWidgets('keduanya aktif: DEV menang', (t) async {
    await t.pumpWidget(_host(beta: true, dev: true));
    expect(find.byType(Banner), findsOneWidget);
    expect(t.widget<Banner>(find.byType(Banner)).message, 'DEV · uji lokal');
  });
}
