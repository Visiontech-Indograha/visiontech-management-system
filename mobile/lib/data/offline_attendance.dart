import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:drift/drift.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import '../core/api_client.dart';
import '../core/device_id.dart';
import '../core/error_message.dart';
import 'app_database.dart';
import 'vms_api.dart';

/// Absen lapangan offline (R-34, keputusan pemilik 2026-10-02 — mengubah K-13).
///
/// Disimpan di mana: antrean SQLite aplikasi (`pending_sync_operations`, jenis
/// [entityType]) di penyimpanan INTERNAL aplikasi, dan swafotonya di folder
/// internal `offline_attendance/` — keduanya tidak terlihat dari pengelola file.
///
/// Tidak bisa diubah: setiap catatan ditandatangani kunci EC di Android Keystore
/// (tidak bisa dikeluarkan dari HP). Tanggal/jam/lokasi/alasan/swafoto yang
/// diubah setelah direkam membuat tanda tangannya tidak cocok → ditolak server.
/// Jam tidak diambil dari jam HP: jangkar jam server (bertanda tangan server)
/// + penghitung waktu internal Android, dibandingkan waktu satelit GPS.
class OfflineAttendance {
  OfflineAttendance({
    required AppDatabase db,
    required VmsApi api,
    required DeviceIdProvider deviceId,
  }) : _db = db, // ignore: prefer_initializing_formals
       _api = api, // ignore: prefer_initializing_formals
       _deviceId = deviceId; // ignore: prefer_initializing_formals

  final AppDatabase _db;
  final VmsApi _api;
  final DeviceIdProvider _deviceId;

  static const entityType = 'attendance_offline';
  static const _channel = MethodChannel('vms/attendance_attest');
  static const _storage = FlutterSecureStorage();
  static const _anchorKey = 'vms_time_anchor';
  static const _deviceKeyFlag = 'vms_attendance_device_key';
  static const _uuid = Uuid();

  Future<Map<String, int>> _clock() async {
    final c = Map<String, dynamic>.from(
      await _channel.invokeMethod('clock') as Map,
    );
    return {
      'elapsed_ms': (c['elapsed_ms'] as num).toInt(),
      'boot_count': (c['boot_count'] as num).toInt(),
    };
  }

  /// Simpan jangkar waktu dari server setiap kali daftar absensi berhasil dimuat (online).
  Future<void> saveAnchor(String? token) async {
    if (token == null || token.isEmpty) return;
    final clock = await _clock();
    await _storage.write(
      key: _anchorKey,
      value: jsonEncode({'token': token, ...clock}),
    );
  }

  /// Daftarkan kunci publik Keystore perangkat ini ke server (sekali per akun & perangkat).
  Future<void> ensureDeviceKey(String userId) async {
    final deviceId = await _deviceId.getClientId();
    final flag = '$userId:$deviceId';
    if (await _storage.read(key: _deviceKeyFlag) == flag) return;
    final publicKey = await _channel.invokeMethod<String>('publicKey');
    await _api.registerDeviceKey(deviceId: deviceId, publicKey: publicKey!);
    await _storage.write(key: _deviceKeyFlag, value: flag);
  }

  /// Rekam satu absen offline (masuk/pulang): tandatangani lalu simpan ke antrean.
  Future<void> record({
    required String kind,
    required Map<String, dynamic> site,
    required double lat,
    required double lng,
    required double? accuracyM,
    required bool mocked,
    required DateTime? gpsTime,
    String? explanation,
    File? selfie,
    File? evidence,
  }) async {
    final anchorRaw = await _storage.read(key: _anchorKey);
    final anchor = anchorRaw == null
        ? null
        : Map<String, dynamic>.from(jsonDecode(anchorRaw) as Map);
    final clock = await _clock();
    final opId = _uuid.v4();
    String? selfiePath;
    String? selfieSha;
    if (selfie != null) {
      final dir = Directory(
        '${(await getApplicationSupportDirectory()).path}/offline_attendance',
      );
      await dir.create(recursive: true);
      final internal = await selfie.copy('${dir.path}/$opId.jpg');
      await selfie.delete().catchError((_) => selfie);
      selfiePath = internal.path;
      selfieSha = await _channel.invokeMethod<String>('sha256', {
        'path': internal.path,
      });
    }
    // Foto bukti biasa (di luar radius): disimpan terpisah, TIDAK ikut tanda tangan wajah dan tidak dicocokkan.
    String? evidencePath;
    if (evidence != null) {
      final dir = Directory(
        '${(await getApplicationSupportDirectory()).path}/offline_attendance',
      );
      await dir.create(recursive: true);
      final internal = await evidence.copy('${dir.path}/$opId-bukti.jpg');
      await evidence.delete().catchError((_) => evidence);
      evidencePath = internal.path;
    }
    final payload = jsonEncode({
      'client_op_id': opId,
      'kind': kind,
      'device_id': await _deviceId.getClientId(),
      'site_id': site['id'],
      'site_name': site['name'],
      'lat': lat,
      'lng': lng,
      'accuracy_m': accuracyM,
      'mocked': mocked,
      'anchor_token': anchor?['token'],
      'anchor_elapsed_ms': anchor?['elapsed_ms'],
      'anchor_boot_count': anchor?['boot_count'],
      'event_elapsed_ms': clock['elapsed_ms'],
      'event_boot_count': clock['boot_count'],
      'gps_time_ms': gpsTime?.millisecondsSinceEpoch,
      // Hanya informasi: jam HP TIDAK dipakai server untuk menentukan jam absen.
      'device_time_ms': DateTime.now().millisecondsSinceEpoch,
      'explanation': explanation,
      'selfie_sha256': selfieSha,
    });
    final signature = await _channel.invokeMethod<String>('sign', {
      'data': payload,
    });
    await _db
        .into(_db.pendingSyncOperations)
        .insert(
          PendingSyncOperationsCompanion.insert(
            entityType: entityType,
            payloadJson: jsonEncode({
              'client_op_id': opId,
              'kind': kind,
              // Hanya untuk tampilan antrean; tidak dipakai server.
              'client_created_at': DateTime.now().toUtc().toIso8601String(),
              'payload': payload,
              'signature': signature,
              'selfie_path': selfiePath,
              'selfie_file_id': null,
              'evidence_path': evidencePath,
              'evidence_file_id': null,
            }),
          ),
        );
  }

  /// Absen offline yang belum terkirim (untuk kartu "hari ini" & riwayat).
  Future<List<Map<String, dynamic>>> pending() async {
    final rows =
        await (_db.select(_db.pendingSyncOperations)
              ..where((t) => t.entityType.equals(entityType))
              ..orderBy([(t) => OrderingTerm.asc(t.id)]))
            .get();
    return [
      for (final row in rows)
        () {
          final rec = Map<String, dynamic>.from(
            jsonDecode(row.payloadJson) as Map,
          );
          final p = Map<String, dynamic>.from(
            jsonDecode(rec['payload'] as String) as Map,
          );
          return {
            'kind': rec['kind'],
            'site_name': p['site_name'],
            'device_time_ms': p['device_time_ms'],
            'dead': row.deadLetter,
            'error': row.lastError,
          };
        }(),
    ];
  }

  /// Kirim antrean absen offline berurutan. Berhenti saat jaringan putus; ditolak server → "Perlu perhatian".
  Future<void> push() async {
    final rows =
        await (_db.select(_db.pendingSyncOperations)
              ..where(
                (t) =>
                    t.entityType.equals(entityType) &
                    t.deadLetter.equals(false),
              )
              ..orderBy([(t) => OrderingTerm.asc(t.id)]))
            .get();
    final deviceId = await _deviceId.getClientId();
    for (final row in rows) {
      final rec = Map<String, dynamic>.from(jsonDecode(row.payloadJson) as Map);
      try {
        final path = rec['selfie_path'] as String?;
        if (path != null && rec['selfie_file_id'] == null) {
          rec['selfie_file_id'] = await _api.uploadFile(File(path));
          await (_db.update(
            _db.pendingSyncOperations,
          )..where((t) => t.id.equals(row.id))).write(
            PendingSyncOperationsCompanion(payloadJson: Value(jsonEncode(rec))),
          );
        }
        final evPath = rec['evidence_path'] as String?;
        if (evPath != null && rec['evidence_file_id'] == null) {
          rec['evidence_file_id'] = await _api.uploadFile(File(evPath));
          await (_db.update(
            _db.pendingSyncOperations,
          )..where((t) => t.id.equals(row.id))).write(
            PendingSyncOperationsCompanion(payloadJson: Value(jsonEncode(rec))),
          );
        }
        await _api.submitOfflineAttendance(
          deviceId: deviceId,
          clientOpId: rec['client_op_id'] as String,
          kind: rec['kind'] as String,
          payload: rec['payload'] as String,
          signature: rec['signature'] as String,
          selfieFileId: rec['selfie_file_id'] as String?,
          evidenceFileId: rec['evidence_file_id'] as String?,
        );
        await (_db.delete(
          _db.pendingSyncOperations,
        )..where((t) => t.id.equals(row.id))).go();
        if (path != null) {
          await File(path).delete().catchError((_) => File(path));
        }
        if (evPath != null) {
          await File(evPath).delete().catchError((_) => File(evPath));
        }
      } on DioException catch (e) {
        // Gangguan sementara (tanpa sinyal, sesi sedang diperbarui, server bermasalah): berhenti dan
        // coba lagi nanti — urutan dijaga supaya absen pulang tidak terkirim sebelum absen masuknya.
        final status = e.response?.statusCode;
        if (isNetworkFailure(e) || status == 401 || (status ?? 0) >= 500) {
          return;
        }
        await (_db.update(
          _db.pendingSyncOperations,
        )..where((t) => t.id.equals(row.id))).write(
          PendingSyncOperationsCompanion(
            deadLetter: const Value(true),
            attemptCount: Value(row.attemptCount + 1),
            lastError: Value(apiErrorMessage(e)),
          ),
        );
      } on FileSystemException {
        await (_db.update(
          _db.pendingSyncOperations,
        )..where((t) => t.id.equals(row.id))).write(
          const PendingSyncOperationsCompanion(
            deadLetter: Value(true),
            lastError: Value('Swafoto absen offline tidak ditemukan di HP.'),
          ),
        );
      }
    }
  }
}
