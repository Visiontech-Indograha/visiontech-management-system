import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/gallery_save.dart';
import 'package:vms_mobile/core/theme/vms_sizes.dart';
import 'package:vms_mobile/core/theme/vms_theme.dart';
import 'package:vms_mobile/features/attendance/nearest_site.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/profile/profile_screen.dart';

void main() {
  final sites = [
    {'id': 'a'},
    {'id': 'kantor'},
    {'id': 'c'},
  ];

  test('B-19 lokasi bawaan: kantor sendiri bila tak ada GPS/riwayat; filter id tak relevan', () {
    expect(defaultSiteId(sites, ownOfficeId: 'kantor'), 'kantor');
    expect(defaultSiteId(sites, near: 'c', ownOfficeId: 'kantor'), 'c');
    expect(defaultSiteId(sites, last: 'a', ownOfficeId: 'kantor'), 'a');
    expect(defaultSiteId(sites, ownOfficeId: 'hilang'), 'a');
    expect(ownOfficeFirst(sites, 'kantor').first['id'], 'kantor');
    expect(ownOfficeFirst(sites, null).first['id'], 'a');
    final u = AuthUser.fromJson({'user_id': 'u', 'email': 'e', 'role': 'MEMBER', 'office_id': 'kantor'});
    expect(u.officeId, 'kantor');
  });

  testWidgets('B-31 galat galeri tampil satu pesan awam, tidak menumpuk', (tester) async {
    late BuildContext ctx;
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: Builder(builder: (c) {
      ctx = c;
      return const SizedBox();
    }))));
    showGalleryError(ctx, const GallerySaveException('Foto gagal disimpan ke galeri HP.'), fallback: 'x');
    showGalleryError(ctx, Exception('teknis'), fallback: 'Foto tidak dapat dihapus.');
    await tester.pumpAndSettle();
    expect(find.byType(SnackBar), findsOneWidget);
    expect(find.text('Foto tidak dapat dihapus.'), findsOneWidget);
    expect(find.textContaining('Exception'), findsNothing);
  });

  testWidgets('B-44 sheet foto profil menutup lewat tombol Tutup', (tester) async {
    String? hasil = 'belum';
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: Builder(builder: (c) {
      return TextButton(
        onPressed: () async {
          hasil = await showModalBottomSheet<String>(context: c, builder: (_) => const ProfilePhotoSheet(hasPhoto: true));
        },
        child: const Text('buka'),
      );
    }))));
    await tester.tap(find.text('buka'));
    await tester.pumpAndSettle();
    expect(find.text('Hapus foto'), findsOneWidget);
    await tester.tap(find.byKey(const Key('profile-photo-sheet-close')));
    await tester.pumpAndSettle();
    expect(find.text('Tutup'), findsNothing);
    expect(hasil, isNull);
  });

  testWidgets('B-46 IconButton dan TextButton minimal 48dp lewat token tema', (tester) async {
    await tester.pumpWidget(MaterialApp(
      theme: VmsTheme.light,
      home: Scaffold(
        body: Column(children: [
          IconButton(key: const Key('i'), onPressed: () {}, icon: const Icon(Icons.delete_outline, size: 16), padding: EdgeInsets.zero),
          TextButton(key: const Key('t'), onPressed: () {}, child: const Text('Ok')),
        ]),
      ),
    ));
    expect(VmsSizes.minTap, 48);
    for (final k in ['i', 't']) {
      final s = tester.getSize(find.byKey(Key(k)));
      expect(s.width >= 48 && s.height >= 48, isTrue, reason: '$k = $s');
    }
  });
}
