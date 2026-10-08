import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/session_policy.dart';

/// Buat JWT palsu (tanda tangan tidak valid — memang tidak diverifikasi di
/// sisi klien) berisi klaim yang diminta.
String _fakeJwt(Map<String, dynamic> payload) {
  String seg(Map<String, dynamic> m) =>
      base64Url.encode(utf8.encode(jsonEncode(m))).replaceAll('=', '');
  return '${seg({'alg': 'HS256', 'typ': 'JWT'})}.${seg(payload)}.signature';
}

int _epoch(DateTime t) => t.toUtc().millisecondsSinceEpoch ~/ 1000;

void main() {
  group('authTimeFromJwt', () {
    test('membaca klaim auth_time dari token yang benar', () {
      final token = _fakeJwt({'sub': 'fs_budi', 'auth_time': 1757700000});
      expect(SessionPolicy.authTimeFromJwt(token), 1757700000);
    });

    test('menerima auth_time berupa string', () {
      final token = _fakeJwt({'auth_time': '1757700000'});
      expect(SessionPolicy.authTimeFromJwt(token), 1757700000);
    });

    test('null untuk token tanpa klaim auth_time', () {
      expect(SessionPolicy.authTimeFromJwt(_fakeJwt({'sub': 'x'})), isNull);
    });

    test('null untuk token yang bentuknya rusak, bukan melempar exception', () {
      expect(SessionPolicy.authTimeFromJwt('bukan-jwt'), isNull);
      expect(SessionPolicy.authTimeFromJwt('a.b'), isNull);
      expect(SessionPolicy.authTimeFromJwt('a.@@@.c'), isNull);
      expect(SessionPolicy.authTimeFromJwt(null), isNull);
    });
  });

  group('expiryFor — mana yang lebih dulu antara 24 jam & cutoff 02:00', () {
    test('login pagi ditutup pukul 02:00 dini hari berikutnya, bukan 24 jam', () {
      // Login 08:00 Senin -> 24 jam = 08:00 Selasa, cutoff = 02:00 Selasa.
      // Cutoff lebih dulu.
      final authTime = DateTime(2026, 9, 14, 8);
      expect(SessionPolicy.expiryFor(authTime), DateTime(2026, 9, 15, 2));
    });

    test('login lewat tengah malam ditutup pukul 02:00 di hari yang sama', () {
      // Login 00:30 -> cutoff 02:00 hari itu juga (1,5 jam kemudian).
      final authTime = DateTime(2026, 9, 14, 0, 30);
      expect(SessionPolicy.expiryFor(authTime), DateTime(2026, 9, 14, 2));
    });

    test('login tepat pukul 02:00 ditutup pukul 02:00 besok, bukan seketika', () {
      final authTime = DateTime(2026, 9, 14, 2);
      expect(SessionPolicy.expiryFor(authTime), DateTime(2026, 9, 15, 2));
    });

    test('login pukul 03:00 dini hari: batas 24 jam yang lebih dulu tercapai', () {
      // Login 03:00 Senin -> cutoff berikutnya 02:00 Selasa (23 jam),
      // 24 jam = 03:00 Selasa. Cutoff tetap lebih dulu.
      final authTime = DateTime(2026, 9, 14, 3);
      expect(SessionPolicy.expiryFor(authTime), DateTime(2026, 9, 15, 2));
    });
  });

  group('isExpired', () {
    final authTime = DateTime(2026, 9, 14, 8); // login 08:00
    final epoch = _epoch(authTime);

    test('belum kedaluwarsa beberapa jam setelah login', () {
      expect(
        SessionPolicy.isExpired(epoch, now: DateTime(2026, 9, 14, 17)),
        isFalse,
      );
    });

    test('belum kedaluwarsa tepat sebelum cutoff', () {
      expect(
        SessionPolicy.isExpired(epoch, now: DateTime(2026, 9, 15, 1, 59)),
        isFalse,
      );
    });

    test('kedaluwarsa tepat pada cutoff 02:00', () {
      expect(
        SessionPolicy.isExpired(epoch, now: DateTime(2026, 9, 15, 2)),
        isTrue,
      );
    });

    test('kedaluwarsa jauh setelah cutoff', () {
      expect(
        SessionPolicy.isExpired(epoch, now: DateTime(2026, 9, 20, 9)),
        isTrue,
      );
    });

    test(
        'auth_time null dianggap MASIH berlaku — sesi lama sebelum fitur ini '
        'tidak boleh melempar user yang sedang bekerja ke layar login', () {
      expect(SessionPolicy.isExpired(null, now: DateTime(2030)), isFalse);
    });
  });
}
