import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../core/error_message.dart';
import '../../core/geofence_confirm.dart';
import '../../core/local_storage.dart';
import '../../core/location_helper.dart';
import '../../core/photo_capture.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../data/sync_engine.dart';
import '../../data/vms_api.dart' show isCursorRejected, kPesanKursorBerubah;
import '../../shared/ui/vms_select_field.dart';
import '../../shared/ui/vms_ui.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import '../face/face_enroll_gate.dart';
import '../notifications/notifications_screen.dart' show NotificationBell;
import '../plans/daily_plan_screen.dart';
import 'nearest_site.dart';
import 'session_labels.dart';

/// Absensi (M5, dok 05 §3.5). Wajib online: waktu & geofence ditentukan server.
/// Di luar radius lokasi, server mewajibkan swafoto — aplikasi memintanya lebih dulu.
class AttendanceScreen extends ConsumerStatefulWidget {
  const AttendanceScreen({super.key});

  @override
  ConsumerState<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends ConsumerState<AttendanceScreen> {
  List<Map<String, dynamic>> _records = [];
  // R-34: absen offline yang belum terkirim (antrean bertanda tangan di HP).
  List<Map<String, dynamic>> _offline = [];
  String? _serverToday;
  // Jam wajib pulang & jumlah tugas belum dilapor hari ini (dari server): dasar pengingat dan peringatan laporan.
  DateTime? _requiredOutAt;
  int _reportPending = 0;
  String? _reportPlanId;
  List<Map<String, dynamic>> _sites = [];
  String? _siteId;
  // Lokasi SK yang sedang berjalan untuk akun ini (dasar peringatan bila memilih lokasi lain).
  List<String> _runningSites = [];
  DateTime? _cachedAt;
  bool _loading = true;
  bool _busy = false;
  String? _error;
  bool _faceEnrolled = false;
  // Paginasi keyset riwayat: kursor halaman berikut (null = sudah habis atau data dari cache).
  String? _nextCursor;
  bool _memuatLagi = false;

  static final _day = DateFormat('EEE, d MMM yyyy', 'id_ID');
  static final _time = DateFormat('HH:mm');

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _siteName(String id) => (_sites.where((s) => s['id'] == id).firstOrNull?['name'] as String?) ?? 'penugasan';

  String get _employeeId {
    final auth = ref.read(authControllerProvider);
    return auth is AuthAuthenticated ? auth.user.employeeId : '';
  }

  Map<String, int> _summary = const {};
  bool _siteManual = false; // pengguna memilih lokasi sendiri → jangan diganti otomatis

  /// Tanpa tugas berjalan: setelah titik GPS pertama tiba, pindah ke lokasi terdekat (bila pengguna belum memilih).
  Future<void> _autoPickNearest() async {
    if (_siteManual || _runningSites.isNotEmpty || _sites.length < 2) return;
    final fix = await LocationWarmer.instance.waitForFix();
    if (fix == null || !mounted || _siteManual) return;
    final near = nearestSiteId(_sites, fix.latitude, fix.longitude);
    if (near != null && near != _siteId) setState(() => _siteId = near);
  }

  /// Ringkasan antrean (best-effort): gagal/offline → kartu disembunyikan, tidak mengganggu absensi.
  Future<void> _loadSummary() async {
    try {
      final s = await ref.read(syncEngineProvider).api.homeSummary();
      if (mounted) setState(() => _summary = s);
    } catch (_) {}
  }

  /// Muat halaman riwayat berikut (keyset). Kursor ditolak (422) = muat ulang dari awal.
  Future<void> _muatLagi() async {
    final cursor = _nextCursor;
    if (cursor == null || _memuatLagi) return;
    setState(() => _memuatLagi = true);
    try {
      final res = await ref
          .read(syncEngineProvider)
          .api
          .myAttendance(employeeId: _employeeId, cursor: cursor);
      if (!mounted) return;
      setState(() {
        _records = [..._records, ...res.items];
        _nextCursor = res.nextCursor;
        _memuatLagi = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _memuatLagi = false);
      if (isCursorRejected(e)) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text(kPesanKursorBerubah)));
        await _load();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(apiErrorMessage(e, fallback: 'Riwayat belum bisa dimuat. Coba lagi.'))),
        );
      }
    }
  }

  Future<void> _load() async {
    unawaited(_loadSummary());
    setState(() {
      _loading = true;
      _error = null;
    });
    final engine = ref.read(syncEngineProvider);
    final offline = engine.offlineAttendance;
    _offline = await offline.pending();
    _nextCursor = null;
    try {
      String? anchor;
      final att = await engine.fetchList('attendance', () async {
        final res = await engine.api.myAttendance(employeeId: _employeeId);
        _serverToday = res.today;
        _requiredOutAt = DateTime.tryParse(res.requiredOutAt ?? '');
        _reportPending = res.reportPendingCount;
        _reportPlanId = res.reportPendingPlanId;
        anchor = res.timeAnchor;
        _nextCursor = res.nextCursor;
        return res.items;
      });
      // R-34: saat online, simpan jangkar jam server & daftarkan kunci Keystore untuk absen offline.
      if (anchor != null) {
        await offline.saveAnchor(anchor);
        final auth = ref.read(authControllerProvider);
        if (auth is AuthAuthenticated) {
          await offline.ensureDeviceKey(auth.user.id).catchError((_) {});
        }
      }
      final sites = await engine.fetchList('sites', engine.api.sites);
      // Lokasi tugas hari ini (jadwal harian tim yang disetujui/berjalan) juga target absen sah (docs/35 §5):
      // id = daily_plan_id, didahulukan di atas kantor.
      // Tanggal server (WIB) bila sudah diketahui; jam HP bisa salah atau beda zona.
      final today = _serverToday ??
          DateFormat('yyyy-MM-dd').format(
              DateTime.now().toUtc().add(const Duration(hours: 7)));
      final plans = await engine.fetchList('daily_today', () => engine.api.dailyPlans(start: today, end: today));
      if (!NetworkHint.probablyOffline) {
        try {
          final fs = await engine.api.faceStatus();
          _faceEnrolled = fs['enrolled'] == true;
        } catch (_) {
          _faceEnrolled = false;
        }
      }
      final daySites = [
        for (final p in plans.items)
          if ((p['status'] == 'APPROVED' || p['status'] == 'ONGOING') &&
              p['site_lat'] != null &&
              p['site_lng'] != null &&
              p['attendance_radius_m'] != null)
            {
              'id': p['daily_plan_id'],
              'name': 'Lokasi tugas: ${p['site_name'] ?? 'Site'}',
              'location': {'lat': num.parse('${p['site_lat']}'), 'lng': num.parse('${p['site_lng']}')},
              'radius_m': p['attendance_radius_m'],
            },
      ];
      final runningSites = [for (final d in daySites) d['id'] as String];
      if (!mounted) return;
      setState(() {
        _records = att.items;
        _runningSites = runningSites;
        _sites = [...daySites, ...sites.items];
        // Offline & belum pernah termuat → pesan jelas, bukan "data terakhir 1 Jan 1970".
        final never = SyncEngine.neverCached(att.cachedAt);
        _cachedAt = never ? null : att.cachedAt;
        _error = never ? SyncEngine.offlineNoDataMessage : null;
        // Titik SK berjalan diubah PM → pilihan ikut pindah; pilihan manual lain tetap dihormati.
        final keep =
            _siteId != null &&
            _sites.any((s) => s['id'] == _siteId) &&
            (runningSites.isEmpty || runningSites.contains(_siteId));
        if (!keep) {
          // Tanpa tugas berjalan: pilih lokasi terdekat dari titik GPS terakhir yang segar (bila ada).
          final fix = runningSites.isEmpty ? LocationWarmer.instance.freshFix() : null;
          final near = fix == null ? null : nearestSiteId(_sites, fix.latitude, fix.longitude);
          _siteId = near ?? (_sites.isNotEmpty ? _sites.first['id'] as String : null);
        }
      });
      unawaited(_autoPickNearest());
      await _syncReminders();
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Kartu "Absensi hari ini" (O-10). Sesi yang masih terbuka didahulukan: server menolak absen
  /// masuk selama ada sesi terbuka, jadi tombol absen pulang harus tetap muncul lewat tengah malam.
  /// Selain itu pakai tanggal dari server (zona waktu organisasi); jam HP hanya cadangan saat offline.
  /// Label tombol pulang; bila sesi yang dibuka berasal dari hari lain, sebut tanggalnya agar tidak membingungkan.
  String _openSessionLabel(Map<String, dynamic> today) {
    final day = today['work_date'] as String?;
    final current = _serverToday ?? DateFormat('yyyy-MM-dd').format(DateTime.now());
    if (day == null || day == current) return 'Absen pulang';
    return 'Absen pulang (masuk ${DateFormat('d MMM', 'id_ID').format(DateTime.parse(day))})';
  }

  Map<String, dynamic>? get _today {
    // R-34: absen offline yang belum terkirim tampil sebagai absensi hari ini.
    final offIn = _offline.where((o) => o['kind'] == 'CHECK_IN' && o['dead'] != true).lastOrNull;
    final offOut = _offline.where((o) => o['kind'] == 'CHECK_OUT' && o['dead'] != true).lastOrNull;
    String iso(Map o) => DateTime.fromMillisecondsSinceEpoch(o['device_time_ms'] as int).toIso8601String();
    if (offIn != null) {
      return {
        'site_label': offIn['site_name'],
        'check_in_at': iso(offIn),
        'check_out_at': offOut == null ? null : iso(offOut),
        'status': 'OFFLINE',
      };
    }
    // R-33: hanya sesi valid yang bisa absen pulang; absen hari lalu yang menunggu pemeriksaan tidak
    // mengunci hari baru, jadi tidak didahulukan di kartu "hari ini". Sesi tanggal sebelumnya (lupa pulang,
    // kerja malam) sudah berakhir pada tengah malam: tidak ditawarkan sebagai "Absen pulang" hari ini.
    final dayNow = _serverToday ?? DateFormat('yyyy-MM-dd').format(DateTime.now());
    for (final r in _records) {
      if (r['check_in_at'] != null &&
          r['check_out_at'] == null &&
          r['work_date'] == dayNow &&
          (r['status'] == 'AUTO_VALID' || r['status'] == 'APPROVED')) {
        // Absen pulang offline yang belum terkirim: tampilkan jamnya & jangan tawarkan pulang lagi.
        if (offOut != null) {
          return {...r, 'check_out_at': iso(offOut), 'checkout_offline': true};
        }
        return r;
      }
    }
    final today = _serverToday ?? DateFormat('yyyy-MM-dd').format(DateTime.now());
    for (final r in _records) {
      if (r['work_date'] == today) return r;
    }
    return null;
  }

  /// Keputusan pemilik 2026-10-02: ditolak → boleh mengajukan ulang sekali; ditolak lagi →
  /// hari itu terkunci dan tercatat ditolak (server menolak dengan ATTENDANCE_DAY_LOCKED).
  static const _maxAttemptsPerDay = 2;

  int get _rejectedToday {
    final today = _serverToday ?? DateFormat('yyyy-MM-dd').format(DateTime.now());
    return _records.where((r) => r['work_date'] == today && r['status'] == 'REJECTED').length;
  }

  void _snack(String msg) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  Future<Position?> _position() async {
    final loc = await getCurrentPositionSafely();
    if (loc.position == null) {
      _snack(loc.errorMessage ?? 'Lokasi tidak tersedia.');
      return null;
    }
    if (loc.isMocked) {
      _snack('Lokasi palsu terdeteksi. Matikan aplikasi pemalsu lokasi.');
      return null;
    }
    return loc.position;
  }

  /// Susun ulang alarm pengingat absen (masuk 07:30–08:00, pulang dari jam wajib pulang) sesuai keadaan terbaru.
  Future<void> _syncReminders() async {
    final today = _today;
    final checkedIn = today != null && today['check_in_at'] != null;
    final checkedOut = today != null && today['check_out_at'] != null;
    var requiredOut = _requiredOutAt;
    if (requiredOut == null && checkedIn) {
      requiredOut = DateTime.tryParse('${today['check_in_at']}')?.add(const Duration(hours: 9));
    }
    try {
      await ref.read(attendanceRemindersProvider).sync(
        serverToday: _serverToday,
        checkedIn: checkedIn,
        checkedOut: checkedOut,
        requiredOut: requiredOut,
      );
    } catch (_) {
      // Pengingat hanya bantuan; kegagalan penjadwalan tidak boleh mengganggu layar absen.
    }
  }

  /// Peringatan laporan harian: ada tugas hari ini yang progresnya belum diperbarui. Tidak memblokir absen.
  Future<bool> _confirmDailyReport() async {
    if (_reportPending <= 0) return true;
    if (!mounted) return false;
    final choice = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Laporan harian belum diisi'),
        content: Text(
          'Ada $_reportPending tugas hari ini yang progresnya belum kamu perbarui. '
          'Isi laporan harian dulu sebelum absen pulang.',
        ),
        actions: [
          if (_reportPlanId != null)
            TextButton(onPressed: () => Navigator.pop(ctx, 'report'), child: const Text('Isi laporan')),
          FilledButton(onPressed: () => Navigator.pop(ctx, 'go'), child: const Text('Tetap absen pulang')),
        ],
      ),
    );
    if (choice == 'report' && mounted) {
      await Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => DailyPlanScreen(dailyPlanId: _reportPlanId!)),
      );
      await _load();
      return false;
    }
    return choice == 'go';
  }

  Future<void> _checkIn() async {
    final now = attendanceClock();
    if (!attendanceHoursSkipped() && _wibMinutes(now) < 6 * 60 + 45) {
      await tampilkanJamBukaAbsen(context);
      return;
    }
    final site = _sites.where((s) => s['id'] == _siteId).firstOrNull;
    if (site == null) return _snack('Pilih lokasi kerja dulu.');
    setState(() => _busy = true);
    try {
      final pos = await _position();
      if (pos == null) return;
      // K-12: server menolak akurasi > 100 m — beri tahu sebelum meminta swafoto.
      if (pos.accuracy > maxGpsAccuracyM) {
        return _snack(gpsAccuracyMessage(pos.accuracy));
      }
      final loc = site['location'] as Map;
      final distance = Geolocator.distanceBetween(
        pos.latitude,
        pos.longitude,
        (loc['lat'] as num).toDouble(),
        (loc['lng'] as num).toDouble(),
      );
      final radius = (site['radius_m'] as num?) ?? 50;
      final outside = distance > radius;

      // 1. Lokasi sudah didapat. 2. Di luar zona / ajukan ulang: penjelasan. 3. Swafoto SELALU (docs/35 §5) —
      // server mencocokkannya dengan wajah terdaftar (wajah V2); tidak cocok → ditolak dengan pesan jelas.
      String? explanation;
      if (outside || _rejectedToday > 0) {
        if (!mounted) return;
        explanation = await _askExplanation(
          title: outside ? 'Absen di luar zona' : 'Ajukan absen ulang',
          info: outside
              ? 'Anda sekitar ${formatJarakId(distance)} dari ${site['name']} '
                    '(batas absen ${formatJarakId(radius.toDouble())}). '
                    'Jelaskan mengapa Anda absen di luar lokasi. Setelah dikirim, absen menunggu pemeriksaan atasan.'
              : 'Jelaskan alasan pengajuan ulang absensi yang ditolak.',
        );
        if (explanation == null) return;
      }
      String? selfieId;
      if (!mounted) return;
      if (!await konfirmasiSwafoto(context)) return;
      if (!mounted) return;
      final (selfieFile, err) = await captureWatermarkedPhoto(
        context: context,
        label: 'Swafoto absen masuk',
        kind: LocalFileKind.selfie,
        hint: outside
            ? 'Anda sekitar ${formatJarakId(distance)} dari ${site['name']}. Pastikan wajah terlihat jelas.'
            : 'Pastikan wajah terlihat jelas dan tidak tertutup.',
        preferFrontCamera: true,
      );
      if (selfieFile == null) {
        if (err != null) _snack(err);
        return;
      }
      // Foto BUKTI di luar radius: foto biasa (kamera belakang), TIDAK dicocokkan dengan wajah.
      File? evidenceFile;
      if (outside) {
        if (!mounted) return;
        final (ev, evErr) = await captureWatermarkedPhoto(
          context: context,
          label: 'Foto bukti di luar radius',
          hint: 'Foto lokasi tempat Anda berada sekarang sebagai bukti.',
        );
        if (ev == null) {
          if (evErr != null) _snack(evErr);
          return;
        }
        evidenceFile = ev;
      }
      try {
        final api = ref.read(syncEngineProvider).api;
        selfieId = await api.uploadFile(selfieFile);
        final evidenceId = evidenceFile == null ? null : await api.uploadFile(evidenceFile);
        final inRes = await ref
            .read(syncEngineProvider)
            .api
            .checkIn(
              siteId: site['id'] as String,
              lat: pos.latitude,
              lng: pos.longitude,
              accuracyM: pos.accuracy,
              selfieFileId: selfieId,
              evidenceFileId: evidenceId,
              explanation: explanation,
            );
        _snack('Absen masuk tercatat.');
        // Terlambat: foto bukti biasa (tanpa pencocokan wajah) menyusul; gagal/batal tidak memblokir absen.
        if (inRes['is_late'] == true && evidenceFile == null && inRes['id'] != null) {
          await _addEvidence(inRes['id'] as String, 'Foto bukti keterlambatan', 'Foto lokasi atau keadaan Anda sebagai bukti keterlambatan.');
        }
      } on DioException catch (e) {
        if (!isNetworkFailure(e)) rethrow;
        // R-34: tanpa sinyal — rekam offline bertanda tangan, kirim otomatis saat online.
        await ref
            .read(syncEngineProvider)
            .offlineAttendance
            .record(
              kind: 'CHECK_IN',
              site: site,
              lat: pos.latitude,
              lng: pos.longitude,
              accuracyM: pos.accuracy,
              mocked: pos.isMocked,
              gpsTime: pos.timestamp,
              explanation: explanation,
              selfie: selfieFile,
              evidence: evidenceFile,
            );
        _snack('Tidak ada sinyal — absen masuk tersimpan offline dan dikirim otomatis saat online.');
      }
      await _load();
    } catch (e) {
      if (!await _handleFaceNotEnrolled(e)) _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Foto bukti biasa (kamera belakang, tanpa pencocokan wajah) ditempel ke absensi [attId].
  /// Dibatalkan/gagal: absen tetap tercatat, tombol 'Tambah foto bukti' di kartu absen hari ini tetap ada.
  Future<void> _addEvidence(String attId, String label, String hint) async {
    if (!mounted) return;
    final (file, err) = await captureWatermarkedPhoto(context: context, label: label, hint: hint);
    if (file == null) {
      _snack(err ?? 'Foto bukti belum diambil. Anda bisa menambahkannya lewat tombol "Tambah foto bukti".');
      return;
    }
    try {
      final api = ref.read(syncEngineProvider).api;
      await api.attachAttendanceEvidence(attId, await api.uploadFile(file));
      _snack('Foto bukti tersimpan.');
    } catch (e) {
      _snack('Foto bukti belum terkirim. Coba lagi lewat tombol "Tambah foto bukti". ${apiErrorMessage(e)}');
    }
  }

  Future<void> _checkOut() async {
    final now = attendanceClock();
    if (_wibHour(now) >= 19) {
      _snack('Batas waktu absensi pulang mandiri telah ditutup pada pukul 19:00 WIB (Sistem auto check-out aktif).');
      return;
    }

    if (!await _confirmDailyReport()) return;

    final checkInAtStr = _today?['check_in_at'] as String?;
    if (checkInAtStr != null) {
      final checkInAt = DateTime.tryParse(checkInAtStr)?.toLocal();
      if (checkInAt != null) {
        final grossSec = now.difference(checkInAt).inSeconds;
        if (grossSec < 9 * 3600) {
          final effSec = grossSec > 3600 ? grossSec - 3600 : 0;
          final effH = effSec ~/ 3600;
          final effM = (effSec % 3600) ~/ 60;
          if (!mounted) return;
          final proceed = await showDialog<bool>(
            context: context,
            builder: (ctx) => AlertDialog(
              title: const Text('Waktu Kerja Belum Mencapai 8 Jam'),
              content: Text(
                'Waktu kerja kamu saat ini baru $effH jam $effM menit '
                '(belum mencapai 8 jam kerja efektif, karena 1 jam istirahat tidak termasuk jam kerja).\n\n'
                'Jika tetap melanjutkan pulang sekarang, absensi hari ini akan dicatat dengan status Pulang Cepat. '
                'Yakin ingin tetap absen pulang?',
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
                FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Lanjutkan Pulang Cepat')),
              ],
            ),
          );
          if (proceed != true) return;
        }
      }
    }

    setState(() => _busy = true);
    try {
      final pos = await _position();
      if (pos == null) return;

      // Wajah terdaftar → swafoto pulang dicocokkan server (wajah V2).
      File? outSelfie;
      if (_faceEnrolled) {
        if (!mounted) return;
        if (!await konfirmasiSwafoto(context)) return;
        if (!mounted) return;
        final (file, err) = await captureWatermarkedPhoto(
          context: context,
          label: 'Swafoto absen pulang',
          kind: LocalFileKind.selfie,
          hint: 'Pastikan wajah terlihat jelas dan tidak tertutup.',
          preferFrontCamera: true,
        );
        if (file == null) {
          if (err != null) _snack(err);
          return;
        }
        outSelfie = file;
      }
      // Pulang di luar radius: foto bukti biasa terpisah dari swafoto (tanpa pencocokan wajah).
      File? outEvidence;
      Future<bool> askOutEvidence() async {
        if (!mounted) return false;
        final (ev, evErr) = await captureWatermarkedPhoto(
          context: context,
          label: 'Foto bukti di luar radius',
          hint: 'Foto lokasi tempat Anda berada sekarang sebagai bukti.',
        );
        if (ev == null) {
          if (evErr != null) _snack(evErr);
          return false;
        }
        outEvidence = ev;
        return true;
      }

      final openSite = _sites.where((s) => s['id'] == _today?['site_id']).firstOrNull;
      final openLoc = openSite?['location'];
      if (openSite != null && openLoc is Map) {
        final dist = Geolocator.distanceBetween(
          pos.latitude,
          pos.longitude,
          (openLoc['lat'] as num).toDouble(),
          (openLoc['lng'] as num).toDouble(),
        );
        if (dist > ((openSite['radius_m'] as num?) ?? 50) && !await askOutEvidence()) return;
      }
      Future<void> recordOffline() => ref
          .read(syncEngineProvider)
          .offlineAttendance
          .record(
            kind: 'CHECK_OUT',
            site: {'id': null, 'name': _today?['site_label']},
            lat: pos.latitude,
            lng: pos.longitude,
            accuracyM: pos.accuracy,
            mocked: pos.isMocked,
            gpsTime: pos.timestamp,
            evidence: outEvidence,
          );
      if (_today?['status'] == 'OFFLINE') {
        await recordOffline();
        _snack('Absen pulang tersimpan offline dan dikirim otomatis saat online.');
      } else {
        try {
          final outApi = ref.read(syncEngineProvider).api;
          final outSelfieId = outSelfie == null ? null : await outApi.uploadFile(outSelfie);
          Future<Map<String, dynamic>> sendOut() async => outApi.checkOut(
            lat: pos.latitude,
            lng: pos.longitude,
            accuracyM: pos.accuracy,
            selfieFileId: outSelfieId,
            evidenceFileId: outEvidence == null ? null : await outApi.uploadFile(outEvidence!),
          );
          Map<String, dynamic> res;
          try {
            res = await sendOut();
          } on DioException catch (e) {
            // Data lokasi tak tersedia di HP: server menolak (T7, di luar radius) → minta foto bukti lalu ulangi.
            final msg = apiErrorMessage(e).toLowerCase();
            if (e.response?.statusCode != 422 || outEvidence != null || !(msg.contains('radius') || msg.contains('zona'))) {
              rethrow;
            }
            if (!await askOutEvidence()) return;
            res = await sendOut();
          }
          final encouragement = res['encouragement_message'] as String?;
          if (encouragement != null && encouragement.isNotEmpty && mounted) {
            await showDialog<void>(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Row(
                  children: [
                    Text('🌟 '),
                    Expanded(child: Text('Terima Kasih Atas Kerja Kerasmu!')),
                  ],
                ),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const SizedBox(height: 8),
                    const Center(child: Text('🌟💪', style: TextStyle(fontSize: 40))),
                    const SizedBox(height: 16),
                    Text(encouragement, style: const TextStyle(fontSize: 14, height: 1.4), textAlign: TextAlign.center),
                  ],
                ),
                actions: [
                  FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('Tutup & Selamat Beristirahat')),
                ],
              ),
            );
          } else {
            _snack('Absen pulang tercatat.');
          }
        } on DioException catch (e) {
          if (!isNetworkFailure(e)) rethrow;
          await recordOffline();
          _snack('Tidak ada sinyal — absen pulang tersimpan offline dan dikirim otomatis saat online.');
        }
      }
      await _load();
    } catch (e) {
      if (!await _handleFaceNotEnrolled(e)) _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// T3: server menolak absen karena wajah belum terdaftar → jelaskan, lalu buka gerbang pendaftaran wajah.
  Future<bool> _handleFaceNotEnrolled(Object e) async {
    if (apiErrorCode(e) != 'FACE_NOT_ENROLLED' || !mounted) return false;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Wajah belum terdaftar'),
        content: Text(apiErrorMessage(e)),
        actions: [FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('Daftarkan wajah'))],
      ),
    );
    ref.invalidate(faceGateProvider);
    return true;
  }

  /// Dialog penjelasan wajib: Kirim dengan isian kosong menampilkan pesan, bukan menutup diam-diam.
  /// Mengembalikan teks (sudah di-trim) atau null bila dibatalkan.
  Future<String?> _askExplanation({required String title, String? info, String initial = ''}) {
    final controller = TextEditingController(text: initial);
    String? error;
    return showDialog<String>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialog) => AlertDialog(
          title: Text(title),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (info != null) ...[Text(info, style: VmsTextStyles.bodySm), const SizedBox(height: 12)],
              TextField(
                key: const Key('explanation-field'),
                controller: controller,
                autofocus: true,
                maxLines: 4,
                maxLength: 1000,
                onChanged: (_) {
                  if (error != null) setDialog(() => error = null);
                },
                decoration: InputDecoration(hintText: 'Mis. ban bocor di jalan menuju lokasi', errorText: error),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Batal')),
            FilledButton(
              onPressed: () {
                final text = controller.text.trim();
                if (text.isEmpty) {
                  setDialog(() => error = 'Penjelasan wajib diisi.');
                  return;
                }
                Navigator.pop(ctx, text);
              },
              child: const Text('Kirim'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _explain(Map<String, dynamic> record) async {
    final text = await _askExplanation(title: 'Beri penjelasan', initial: record['explanation'] as String? ?? '');
    if (text == null) return;
    try {
      await ref.read(syncEngineProvider).api.explainAttendance(record['id'] as String, text);
      _snack('Penjelasan terkirim.');
      await _load();
    } catch (e) {
      _snack(apiErrorMessage(e));
    }
  }

  String _hhmm(dynamic iso) => iso == null ? '--:--' : _time.format(DateTime.parse(iso as String).toLocal());

  Widget _timeTile(String label, String value, IconData icon, Accent accent) => Expanded(
    child: Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Row(
        children: [
          Icon(icon, color: VmsColors.gold, size: 22),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: VmsTextStyles.caption.copyWith(color: Colors.white.withValues(alpha: 0.7))),
              Text(
                value,
                style: VmsTextStyles.title.copyWith(color: Colors.white, fontWeight: FontWeight.w800),
              ),
            ],
          ),
        ],
      ),
    ),
  );

  Widget _flag(String text, Accent accent) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(color: accent.soft, borderRadius: BorderRadius.circular(99)),
    child: Text(
      text,
      style: VmsTextStyles.caption.copyWith(color: accent.strong, fontWeight: FontWeight.w700),
    ),
  );

  @override
  Widget build(BuildContext context) {
    // Sinkron latar selesai (mis. absen offline baru terkirim) → muat ulang kartu & riwayat.
    ref.listen(syncTickProvider, (_, _) => _load());
    ref.listen(liveEventTickProvider, (_, _) => _load()); // T8: peristiwa waktu nyata
    final today = _today;
    final auth = ref.watch(authControllerProvider);
    final name = auth is AuthAuthenticated ? auth.user.displayName.split(' ').first : '';
    final lewatWeb = auth is AuthAuthenticated && auth.user.absensiLewatWeb;
    final hour = DateTime.now().hour;
    final greet = hour < 11
        ? 'Selamat pagi'
        : hour < 15
        ? 'Selamat siang'
        : hour < 18
        ? 'Selamat sore'
        : 'Selamat malam';
    return Scaffold(
      appBar: const VmsTopBar(trailing: NotificationBell()),
      body: RefreshIndicator(
        onRefresh: _load,
        edgeOffset: 120,
        child: ListView(
          padding: safeListPadding(context),
          children: [
            HeroHeader(
              eyebrow: 'Absensi',
              title: name.isEmpty ? greet : '$greet, $name',
              subtitle: _day.format(DateTime.now()),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_cachedAt != null)
                    NoticeBanner(
                      icon: Icons.cloud_off_rounded,
                      text: 'Offline — data terakhir ${DateFormat('d MMM HH:mm', 'id_ID').format(_cachedAt!)}',
                    ),
                  if (_error != null)
                    NoticeBanner(icon: Icons.error_outline_rounded, text: _error!, accent: Accent.rose),
                  FadeSlideIn(
                    child: SurfaceCard(
                      highlight: true,
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            children: [
                              const IconTile(icon: Icons.fingerprint_rounded, accent: Accent.indigo),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Absensi hari ini',
                                      style: VmsTextStyles.subheading.copyWith(
                                        fontWeight: FontWeight.w800,
                                        color: Colors.white,
                                      ),
                                    ),
                                    Text(
                                      today == null
                                          ? 'Belum absen masuk'
                                          : '${today['site_label']} · '
                                                '${today['city_category'] == 'LUAR_KOTA' ? 'Luar kota' : 'Dalam kota'}',
                                      style: VmsTextStyles.bodySm.copyWith(color: Colors.white.withValues(alpha: 0.75)),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                              if (today != null) StatusPill(today['status'] as String?),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              _timeTile('Masuk', _hhmm(today?['check_in_at']), Icons.login_rounded, Accent.emerald),
                              const SizedBox(width: 10),
                              _timeTile('Pulang', _hhmm(today?['check_out_at']), Icons.logout_rounded, Accent.rose),
                            ],
                          ),
                          const SizedBox(height: 16),
                          if (lewatWeb)
                            // Pekerja kantor absen lewat web; server juga menolak absen dari HP.
                            const NoticeBanner(
                              key: Key('absen-lewat-web'),
                              icon: Icons.computer_rounded,
                              text:
                                  'Anda terdaftar sebagai pekerja kantor. Absen masuk '
                                  'dan pulang dilakukan lewat web. Riwayat tetap '
                                  'terlihat di sini.',
                            )
                          else if (today == null ||
                              (today['status'] == 'REJECTED' && _rejectedToday < _maxAttemptsPerDay)) ...[
                            if (today != null) ...[
                              NoticeBanner(
                                key: const Key('absen-ditolak-bisa-ulang'),
                                icon: Icons.replay_rounded,
                                accent: Accent.rose,
                                text:
                                    'Absensi ditolak'
                                    '${today['review_note'] != null ? ': ${today['review_note']}' : ''}. '
                                    'Anda dapat mengajukan absen ulang satu kali hari ini.',
                              ),
                              const SizedBox(height: 12),
                            ],
                            if (_sites.isEmpty && _loading) ...[
                              const Padding(
                                padding: EdgeInsets.symmetric(vertical: 12),
                                child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
                              ),
                            ] else if (_sites.isEmpty) ...[
                              const NoticeBanner(
                                key: Key('belum-ada-lokasi-sk'),
                                icon: Icons.location_off_rounded,
                                text:
                                    'Belum ada lokasi kerja untuk akun Anda (lokasi rencana kerja maupun kantor). '
                                    'Hubungi atasan atau admin untuk menambahkan lokasi kerja.',
                              ),
                              const SizedBox(height: 12),
                            ] else ...[
                              VmsSelectField<String>(
                                label: 'Lokasi kerja',
                                icon: Icons.place_rounded,
                                value: _siteId,
                                options: [for (final s in _sites) VmsOption(s['id'] as String, s['name'] as String)],
                                onChanged: (v) => setState(() {
                                  _siteManual = true;
                                  _siteId = v;
                                }),
                              ),
                              const SizedBox(height: 14),
                              // Ada jadwal tugas hari ini tetapi memilih lokasi lain (mis. kantor): hanya peringatan,
                              // absen tetap boleh (keputusan pemilik 2026-10-07).
                              if (_runningSites.isNotEmpty && _siteId != null && !_runningSites.contains(_siteId)) ...[
                                NoticeBanner(
                                  key: const Key('peringatan-bukan-lokasi-sk'),
                                  icon: Icons.warning_amber_rounded,
                                  text:
                                      'Hari ini Anda dijadwalkan di ${_siteName(_runningSites.first)}. Lokasi yang dipilih '
                                      'bukan lokasi tugas; absen tetap bisa dikirim, tetapi pastikan memang bekerja di sini.',
                                ),
                                const SizedBox(height: 14),
                              ],
                            ],
                            PrimaryAction(
                              label: today == null ? 'Absen masuk' : 'Ajukan absen ulang',
                              icon: Icons.login_rounded,
                              gold: true,
                              busy: _busy,
                              onTap: _loading || _sites.isEmpty ? null : _checkIn,
                            ),
                          ] else if ((today['status'] == 'OFFLINE' || today['checkout_offline'] == true) &&
                              today['check_out_at'] != null)
                            NoticeBanner(
                              key: const Key('absen-offline-lengkap'),
                              icon: Icons.cloud_upload_rounded,
                              accent: Accent.indigo,
                              text: today['status'] == 'OFFLINE'
                                  ? 'Absen masuk & pulang tersimpan offline. Dikirim '
                                        'otomatis saat ada sinyal.'
                                  : 'Absen pulang tersimpan offline. Dikirim '
                                        'otomatis saat ada sinyal.',
                            )
                          else if (today['status'] == 'REJECTED')
                            NoticeBanner(
                              key: const Key('absen-hari-ini-terkunci'),
                              icon: Icons.block_rounded,
                              accent: Accent.rose,
                              text:
                                  'Absensi hari ini ditolak $_rejectedToday kali dan '
                                  'tidak dapat diajukan lagi. Hari ini tercatat ditolak.',
                            )
                          else if (today['check_out_at'] == null && today['status'] == 'NEEDS_REVIEW')
                            const NoticeBanner(
                              key: Key('pulang-menunggu-review'),
                              icon: Icons.hourglass_top_rounded,
                              text:
                                  'Absen masuk menunggu pemeriksaan. Absen pulang '
                                  'bisa dilakukan setelah absen masuk disetujui.',
                            )
                          else if (today['check_out_at'] == null && _wibHour(attendanceClock()) >= 19)
                            const NoticeBanner(
                              key: Key('pulang-ditutup'),
                              icon: Icons.schedule_rounded,
                              accent: Accent.indigo,
                              text:
                                  'Absen pulang mandiri ditutup pukul 19:00 WIB. '
                                  'Sistem mencatat pulang otomatis, tidak perlu absen lagi.',
                            )
                          else if (today['check_out_at'] == null)
                            PrimaryAction(
                              label: _openSessionLabel(today),
                              icon: Icons.logout_rounded,
                              gold: true,
                              busy: _busy,
                              onTap: _checkOut,
                            )
                          else
                            const NoticeBanner(
                              icon: Icons.check_circle_rounded,
                              text: 'Absensi hari ini selesai. Terima kasih!',
                              accent: Accent.emerald,
                            ),
                          if (today != null &&
                              today['is_late'] == true &&
                              today['evidence_photo_file_id'] == null &&
                              today['id'] != null &&
                              today['status'] != 'OFFLINE')
                            Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: OutlinedButton.icon(
                                key: const Key('tambah-foto-bukti'),
                                onPressed: _busy
                                    ? null
                                    : () async {
                                        await _addEvidence(
                                          today['id'] as String,
                                          'Foto bukti keterlambatan',
                                          'Foto lokasi atau keadaan Anda sebagai bukti keterlambatan.',
                                        );
                                        await _load();
                                      },
                                icon: const Icon(Icons.add_a_photo_rounded),
                                label: const Text('Tambah foto bukti'),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                  _QueueSummaryCard(summary: _summary, onReturn: _loadSummary),
                  const SectionTitle('Riwayat'),
                  if (_loading)
                    const Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                  if (!_loading && _records.isEmpty && _error == null)
                    const EmptyState(icon: Icons.event_available_rounded, title: 'Belum ada riwayat absensi'),
                  for (final (i, r) in _records.indexed)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: FadeSlideIn(
                        index: i + 1,
                        child: SurfaceCard(
                          padding: const EdgeInsets.all(14),
                          child: Row(
                            children: [
                              IconTile(
                                icon: Icons.calendar_today_rounded,
                                accent: r['is_late'] == true || r['is_early_leave'] == true
                                    ? Accent.amber
                                    : Accent.blue,
                                size: 40,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      _day.format(DateTime.parse(r['work_date'] as String)),
                                      style: VmsTextStyles.bodySm.copyWith(
                                        fontWeight: FontWeight.w700,
                                        color: VmsColors.neutral900,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      '${_hhmm(r['check_in_at'])} – ${_hhmm(r['check_out_at'])}',
                                      style: VmsTextStyles.bodySm.copyWith(color: VmsColors.neutral500),
                                    ),
                                    const SizedBox(height: 6),
                                    Wrap(
                                      spacing: 6,
                                      runSpacing: 4,
                                      children: [
                                        if (r['is_late'] == true) _flag('Terlambat', Accent.amber),
                                        if (isAutoClosedSession(r))
                                          _flag('Lupa absen pulang', Accent.amber)
                                        else if (r['is_early_leave'] == true)
                                          _flag('Pulang awal', Accent.rose),
                                        if (r['explanation'] != null) _flag('Dijelaskan', Accent.indigo),
                                        StatusPill(r['status'] as String?),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                              // Sama dengan server & prototipe (EXPLAIN_ATTENDANCE): hanya absensi
                              // yang menunggu pemeriksaan yang dapat diberi/diubah penjelasannya.
                              if (r['status'] == 'NEEDS_REVIEW')
                                TextButton(
                                  onPressed: () => _explain(r),
                                  child: Text(r['explanation'] == null ? 'Jelaskan' : 'Ubah penjelasan'),
                                ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  if (_nextCursor != null)
                    SizedBox(
                      height: 48,
                      child: OutlinedButton(
                        onPressed: _memuatLagi ? null : _muatLagi,
                        child: Text(_memuatLagi ? 'Memuat...' : 'Muat lebih banyak'),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Jam sekarang di WIB (UTC+7, aturan jam absen server), bukan zona waktu perangkat.
int _wibHour(DateTime now) => now.toUtc().add(const Duration(hours: 7)).hour;

int _wibMinutes(DateTime now) {
  final w = now.toUtc().add(const Duration(hours: 7));
  return w.hour * 60 + w.minute;
}

/// Build development (`VMS_DEVELOPMENT`, juga `--dart-define=VMS_DEVELOPMENT=true`) boleh melewati gerbang jam
/// absen masuk 06:45 di aplikasi bila `VMS_SKIP_ATTENDANCE_HOURS=true`. Build lain selalu dibatasi, flag diabaikan.
const _devBuildFlag = bool.fromEnvironment('VMS_DEVELOPMENT');
const _skipHoursFlag = bool.fromEnvironment('VMS_SKIP_ATTENDANCE_HOURS');

bool attendanceHoursSkipped({bool devBuild = _devBuildFlag, bool skipFlag = _skipHoursFlag}) => devBuild && skipFlag;

/// Pesan jam buka absen sebagai dialog (bukan snackbar yang cepat hilang); tombol OK menutupnya.
Future<void> tampilkanJamBukaAbsen(BuildContext context) {
  return showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Absensi belum dibuka'),
      content: const Text('Absensi masuk baru dibuka mulai pukul 06:45 WIB.'),
      actions: [
        TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('OK')),
      ],
    ),
  );
}

/// Layar singkat sebelum kamera swafoto absen. true bila pengguna menekan Lanjut.
Future<bool> konfirmasiSwafoto(BuildContext context) async {
  final ok = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => AlertDialog(
      title: const Text('Swafoto'),
      content: const Text('Swafoto wajib. Pastikan hanya wajah Anda di depan kamera.'),
      actions: [
        OutlinedButton(
          style: OutlinedButton.styleFrom(minimumSize: const Size(110, 48)),
          onPressed: () => Navigator.pop(ctx, false),
          child: const Text('Batal'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(minimumSize: const Size(110, 48)),
          onPressed: () => Navigator.pop(ctx, true),
          child: const Text('Lanjut'),
        ),
      ],
    ),
  );
  return ok == true;
}

/// Jam untuk aturan jam absen (07.00 masuk, 19.00 batas pulang). Uji membekukannya agar tidak bergantung jam CI.
DateTime Function() attendanceClock = DateTime.now;


/// Kartu "Menunggu tindakan Anda": hanya baris berisi (>0); yang punya layar di HP bisa diketuk.
class _QueueSummaryCard extends StatelessWidget {
  const _QueueSummaryCard({required this.summary, required this.onReturn});

  final Map<String, int> summary;

  /// Dipanggil setelah kembali dari layar tujuan, agar angka tidak basi.
  final Future<void> Function() onReturn;

  static const _rows = <(String, String, String?)>[
    ('leaves_to_review', 'Cuti menunggu keputusan', '/leaves'),
    ('mess_to_review', 'Pengajuan mess menunggu', '/mess'),
    ('loan_requests_to_review', 'Pengajuan pinjam aset menunggu', '/assets'),
    ('attendance_to_review', 'Absensi perlu diperiksa', null),
    ('overtime_to_review', 'Lembur menunggu persetujuan', '/overtime'),
    ('corrections_to_review', 'Koreksi laporan harian menunggu', null),
    ('my_leaves_pending', 'Cuti saya belum diputuskan', '/leaves'),
  ];

  @override
  Widget build(BuildContext context) {
    final rows = [for (final r in _rows) if ((summary[r.$1] ?? 0) > 0) r];
    if (rows.isEmpty) return const SizedBox.shrink();
    return Card(
      margin: const EdgeInsets.only(top: 16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Menunggu tindakan Anda', style: Theme.of(context).textTheme.titleSmall),
            for (final r in rows)
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text(r.$2),
                trailing: Badge(label: Text('${summary[r.$1]}')),
                onTap: r.$3 == null
                    ? null
                    : () async {
                        await context.push(r.$3!);
                        await onReturn();
                      },
              ),
          ],
        ),
      ),
    );
  }
}
