import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/api_client.dart';
import 'package:vms_mobile/core/root_navigator.dart';
import 'package:vms_mobile/core/token_storage.dart';
import 'package:vms_mobile/data/vms_api.dart';
import 'package:vms_mobile/features/auth/auth_controller.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/hse/k3_campaign.dart';
import 'package:vms_mobile/features/hse/k3_campaign_controller.dart';
import 'package:vms_mobile/features/hse/k3_campaign_gate.dart';
import 'package:vms_mobile/features/hse/k3_campaign_view.dart';

import 'support/fake_backend.dart';

K3Campaign campaign({int seconds = 20, int photos = 3, List<String> captions = const []}) => K3Campaign(
  id: 'c1',
  title: 'Uji K3',
  contentText: 'Isi panduan keselamatan kerja.',
  mediaIds: [for (var i = 0; i < photos; i++) 'f$i'],
  mediaCaptions: captions,
  cooldownSeconds: seconds,
);

Future<void> setScreen(WidgetTester tester, double w, double h) async {
  tester.view.physicalSize = Size(w, h);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Widget viewHost(K3Campaign c, {void Function(int)? onConfirm}) => MaterialApp(
  home: K3CampaignView(
    campaign: c,
    onConfirm: onConfirm ?? (_) {},
    photoBuilder: (_, id) => ColoredBox(color: Colors.blue, child: Center(child: Text('foto $id'))),
  ),
);

FilledButton confirmButton(WidgetTester tester) => tester.widget<FilledButton>(find.byType(FilledButton).last);

TransformationController zoomOf(WidgetTester tester) =>
    tester.widget<InteractiveViewer>(find.byType(InteractiveViewer).first).transformationController!;

void main() {
  testWidgets('tombol konfirmasi terkunci sampai waktu habis', (tester) async {
    await setScreen(tester, 360, 800);
    await tester.pumpWidget(viewHost(campaign()));

    expect(confirmButton(tester).onPressed, isNull);
    await tester.pump(const Duration(seconds: 19));
    expect(confirmButton(tester).onPressed, isNull);
    await tester.pump(const Duration(seconds: 2));
    expect(confirmButton(tester).onPressed, isNotNull);
  });

  testWidgets('geser foto tidak mempercepat waktu baca', (tester) async {
    await setScreen(tester, 360, 800);
    await tester.pumpWidget(viewHost(campaign()));

    await tester.fling(find.text('foto f0'), const Offset(-300, 0), 1200);
    await tester.pump(const Duration(seconds: 1));
    await tester.tap(find.text('Selanjutnya'));
    await tester.pump(const Duration(seconds: 17));
    expect(confirmButton(tester).onPressed, isNull);
    await tester.pump(const Duration(seconds: 3));
    expect(confirmButton(tester).onPressed, isNotNull);
  });

  testWidgets('konfirmasi memanggil callback dengan durasi baca', (tester) async {
    await setScreen(tester, 360, 800);
    int? seconds;
    await tester.pumpWidget(viewHost(campaign(seconds: 10), onConfirm: (s) => seconds = s));

    await tester.pump(const Duration(seconds: 11));
    await tester.tap(find.byType(FilledButton).last);
    expect(seconds, greaterThanOrEqualTo(10));
  });

  testWidgets('keterangan foto tampil dan berganti saat pindah foto', (tester) async {
    await setScreen(tester, 360, 800);
    await tester.pumpWidget(viewHost(campaign(captions: const ['Keterangan satu', 'Keterangan dua'])));

    expect(find.text('Keterangan satu'), findsOneWidget);
    await tester.tap(find.text('Selanjutnya'));
    await _settleNav(tester);
    expect(find.text('Keterangan dua'), findsOneWidget);
    expect(find.text('2 dari 3'), findsOneWidget);
  });

  testWidgets('klik dua kali memperbesar foto dan zoom tidak memengaruhi timer', (tester) async {
    await setScreen(tester, 360, 800);
    await tester.pumpWidget(viewHost(campaign(seconds: 10)));

    expect(zoomOf(tester).value.getMaxScaleOnAxis(), closeTo(1, 0.01));
    await doubleTap(tester, find.text('foto f0'));
    expect(zoomOf(tester).value.getMaxScaleOnAxis(), closeTo(2, 0.05));

    await tester.pump(const Duration(seconds: 11));
    expect(confirmButton(tester).onPressed, isNotNull);
  });

  testWidgets('pindah foto mengembalikan zoom ke 1x', (tester) async {
    await setScreen(tester, 360, 800);
    await tester.pumpWidget(viewHost(campaign()));

    await doubleTap(tester, find.text('foto f0'));
    expect(zoomOf(tester).value.getMaxScaleOnAxis(), greaterThan(1.5));

    await tester.tap(find.text('Selanjutnya'));
    await _settleNav(tester);
    expect(zoomOf(tester).value.getMaxScaleOnAxis(), closeTo(1, 0.01));
  });

  testWidgets('tombol Perbesar mengubah transformasi', (tester) async {
    await setScreen(tester, 360, 800);
    await tester.pumpWidget(viewHost(campaign()));

    await tester.tap(find.byTooltip('Perbesar'));
    await tester.pump();
    expect(zoomOf(tester).value.getMaxScaleOnAxis(), closeTo(1.5, 0.05));
    await tester.tap(find.byTooltip('Pas layar'));
    await tester.pump();
    expect(zoomOf(tester).value.getMaxScaleOnAxis(), closeTo(1, 0.01));
  });

  for (final size in const [Size(360, 800), Size(800, 360)]) {
    testWidgets('tata letak ${size.width.toInt()}x${size.height.toInt()} tidak overflow', (tester) async {
      await setScreen(tester, size.width, size.height);
      final long = List.filled(40, 'Kalimat panjang keselamatan kerja.').join(' ');
      await tester.pumpWidget(
        viewHost(
          K3Campaign(
            id: 'c1',
            title: 'Judul kampanye yang sangat panjang sekali untuk menguji pemotongan teks di header',
            contentText: long,
            mediaIds: const ['a', 'b', 'c', 'd', 'e'],
            mediaCaptions: [long, 'Singkat', '', '', ''],
            cooldownSeconds: 60,
          ),
        ),
      );
      await tester.pump();
      expect(tester.takeException(), isNull);
      expect(find.text('Baca keterangan'), findsOneWidget);
      expect(find.byType(FilledButton), findsWidgets);
    });
  }

  testWidgets('gerbang: saat kampanye tampil, back sistem tidak menutupnya dan konfirmasi menutup layar', (tester) async {
    await setScreen(tester, 360, 800);
    final backend = FakeBackend();
    backend.routes['/hse/campaigns/active-popup'] = (_) => {'campaign': _json()};
    final acks = <Map<String, dynamic>>[];
    backend.routes['/hse/campaigns/c1/acknowledge'] = (o) {
      acks.add(Map<String, dynamic>.from(o.data as Map));
      return {'acknowledged': true};
    };
    await tester.pumpWidget(_gateHost(backend));
    await _settle(tester);

    expect(find.text('PANDUAN K3: Uji K3'), findsOneWidget);
    await tester.binding.handlePopRoute();
    await _settle(tester);
    expect(find.text('PANDUAN K3: Uji K3'), findsOneWidget);

    // Selesai membaca → konfirmasi dikirim ke API, layar K3 ditutup.
    await tester.pump(const Duration(seconds: 6));
    await tester.tap(find.byType(FilledButton).last);
    await _settle(tester);
    expect(acks, hasLength(1));
    expect(acks.single['platform'], 'mobile');
    expect(find.text('PANDUAN K3: Uji K3'), findsNothing);
  });

  testWidgets('offline saat cek: diam-diam dilewati, aplikasi tetap tampil', (tester) async {
    await setScreen(tester, 360, 800);
    final backend = FakeBackend(); // tanpa rute = sinyal putus
    await tester.pumpWidget(_gateHost(backend));
    await _settle(tester);

    expect(find.text('ISI-APLIKASI'), findsOneWidget);
    expect(find.textContaining('PANDUAN K3'), findsNothing);
  });
}

Map<String, dynamic> _json() => {
  'campaign_id': 'c1',
  'title': 'Uji K3',
  'content_html': '<p>Isi</p>',
  'media_paths': <String>[],
  'media_path': null,
  'cooldown_seconds': 5,
  'start_date': '2026-01-01',
  'end_date': '2026-12-31',
  'is_mandatory': true,
  'target_audience': 'ALL',
};

class _FakeAuth extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(AuthUser(id: 'u1', username: 'a@b.id', role: UserRole.member, employeeId: 'e1'));
}

Widget _gateHost(FakeBackend backend) {
  final client = ApiClient(tokenStorage: const TokenStorage());
  client.dio.interceptors
    ..clear()
    ..add(backend);
  return ProviderScope(
    overrides: [
      authControllerProvider.overrideWith(_FakeAuth.new),
      k3ApiProvider.overrideWithValue(VmsApi(client)),
    ],
    child: MaterialApp(
      navigatorKey: rootNavigatorKey,
      builder: (context, child) => K3CampaignGate(child: child!),
      home: const Scaffold(body: Text('ISI-APLIKASI')),
    ),
  );
}

/// Klik dua kali cepat (ketuk, jeda singkat, ketuk lagi).
Future<void> doubleTap(WidgetTester tester, Finder finder) async {
  await tester.tap(finder);
  await tester.pump(const Duration(milliseconds: 60));
  await tester.tap(finder);
  await tester.pump();
}

/// Tunggu animasi pindah foto selesai (mulainya tertunda beberapa frame).
Future<void> _settleNav(WidgetTester tester) async {
  for (var i = 0; i < 20; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

/// Pompa berulang tanpa pumpAndSettle (timer layar K3 berjalan terus).
Future<void> _settle(WidgetTester tester) async {
  for (var i = 0; i < 5; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}
