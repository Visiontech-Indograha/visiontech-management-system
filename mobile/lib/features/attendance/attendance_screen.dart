import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../core/error_message.dart';
import '../../core/local_storage.dart';
import '../../core/location_helper.dart';
import '../../core/photo_capture.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../data/sync_engine.dart';
import '../../shared/ui/vms_select_field.dart';
import '../../shared/ui/vms_ui.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import '../face/face_enroll_gate.dart';
import '../face/face_flow.dart';

/// Absensi (M5, dok 05 §3.5). Wajib daring: waktu & geofence ditentukan server.
/// Di luar radius lokasi, server mewajibkan swafoto — aplikasi memintanya lebih dulu.
class AttendanceScreen extends ConsumerStatefulWidget {
  const AttendanceScreen({super.key});

  @override
  ConsumerState<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends ConsumerState<AttendanceScreen> {
  List<Map<String, dynamic>> _records = [];
  // R-34: absen luring yang belum terkirim (antrean bertanda tangan di HP).
  List<Map<String, dynamic>> _offline = [];
  String? _serverToday;
  List<Map<String, dynamic>> _sites = [];
  String? _siteId;
  // Lokasi SK yang sedang berjalan untuk akun ini (dasar peringatan bila memilih lokasi lain).
  List<String> _runningSites = [];
  DateTime? _cachedAt;
  bool _loading = true;
  bool _busy = false;
  String? _error;
  bool _faceEnrolled = false;

  static final _day = DateFormat('EEE, d MMM yyyy', 'id_ID');
  static final _time = DateFormat('HH:mm');

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _siteName(String id) =>
      (_sites.where((s) => s['id'] == id).firstOrNull?['name'] as String?) ??
      'penugasan';

  String get _employeeId {
    final auth = ref.read(authControllerProvider);
    return auth is AuthAuthenticated ? auth.user.employeeId : '';
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final engine = ref.read(syncEngineProvider);
    final offline = engine.offlineAttendance;
    _offline = await offline.pending();
    try {
      String? anchor;
      final att = await engine.fetchList('attendance', () async {
        final res = await engine.api.myAttendance(employeeId: _employeeId);
        _serverToday = res.today;
        anchor = res.timeAnchor;
        return res.items;
      });
      // R-34: saat online, simpan jangkar jam server & daftarkan kunci Keystore untuk absen luring.
      if (anchor != null) {
        await offline.saveAnchor(anchor);
        final auth = ref.read(authControllerProvider);
        if (auth is AuthAuthenticated) {
          await offline.ensureDeviceKey(auth.user.id).catchError((_) {});
        }
      }
      final sites = await engine.fetchList('sites', engine.api.sites);
      final plans = await engine.fetchList('work_plans', engine.api.workPlans);
      try {
        final fs = await engine.api.faceStatus();
        _faceEnrolled = fs['enrolled'] == true;
      } catch (_) {
        _faceEnrolled = false;
      }
      // Titik lokasi SK yang sedang berjalan (ditetapkan PM) didahulukan sebagai lokasi absen.
      // Lokasi absen hari ini mengikuti hari kerja rencana (lokasi khusus hari itu atau lokasi rencana).
      final runningSites = [
        for (final p in plans.items)
          if (todaySiteOf(p) != null) todaySiteOf(p)!,
      ];
      if (!mounted) return;
      setState(() {
        _records = att.items;
        _runningSites = runningSites;
        _sites = [
          ...sites.items.where((s) => runningSites.contains(s['id'])),
          ...sites.items.where((s) => !runningSites.contains(s['id'])),
        ];
        // Luring & belum pernah termuat → pesan jelas, bukan "data terakhir 1 Jan 1970".
        final never = SyncEngine.neverCached(att.cachedAt);
        _cachedAt = never ? null : att.cachedAt;
        _error = never ? SyncEngine.offlineNoDataMessage : null;
        // Titik SK berjalan diubah PM → pilihan ikut pindah; pilihan manual lain tetap dihormati.
        final keep =
            _siteId != null &&
            _sites.any((s) => s['id'] == _siteId) &&
            (runningSites.isEmpty || runningSites.contains(_siteId));
        if (!keep) {
          _siteId = _sites.isNotEmpty ? _sites.first['id'] as String : null;
        }
      });
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Kartu "Absensi hari ini" (O-10). Sesi yang masih terbuka didahulukan: server menolak absen
  /// masuk selama ada sesi terbuka, jadi tombol absen pulang harus tetap muncul lewat tengah malam.
  /// Selain itu pakai tanggal dari server (zona waktu organisasi); jam HP hanya cadangan saat luring.
  Map<String, dynamic>? get _today {
    // R-34: absen luring yang belum terkirim tampil sebagai absensi hari ini.
    final offIn = _offline
        .where((o) => o['kind'] == 'CHECK_IN' && o['dead'] != true)
        .lastOrNull;
    final offOut = _offline
        .where((o) => o['kind'] == 'CHECK_OUT' && o['dead'] != true)
        .lastOrNull;
    String iso(Map o) =>
        DateTime.fromMillisecondsSinceEpoch(o['device_time_ms'] as int)
            .toIso8601String();
    if (offIn != null) {
      return {
        'site_label': offIn['site_name'],
        'check_in_at': iso(offIn),
        'check_out_at': offOut == null ? null : iso(offOut),
        'status': 'OFFLINE',
      };
    }
    // R-33: hanya sesi valid yang bisa absen pulang; absen hari lalu yang menunggu pemeriksaan tidak
    // mengunci hari baru, jadi tidak didahulukan di kartu "hari ini".
    for (final r in _records) {
      if (r['check_in_at'] != null &&
          r['check_out_at'] == null &&
          (r['status'] == 'AUTO_VALID' || r['status'] == 'APPROVED')) {
        // Absen pulang luring yang belum terkirim: tampilkan jamnya & jangan tawarkan pulang lagi.
        if (offOut != null) {
          return {...r, 'check_out_at': iso(offOut), 'checkout_offline': true};
        }
        return r;
      }
    }
    final today =
        _serverToday ?? DateFormat('yyyy-MM-dd').format(DateTime.now());
    for (final r in _records) {
      if (r['work_date'] == today) return r;
    }
    return null;
  }

  /// Keputusan pemilik 2026-10-02: ditolak → boleh mengajukan ulang sekali; ditolak lagi →
  /// hari itu terkunci dan tercatat ditolak (server menolak dengan ATTENDANCE_DAY_LOCKED).
  static const _maxAttemptsPerDay = 2;

  int get _rejectedToday {
    final today =
        _serverToday ?? DateFormat('yyyy-MM-dd').format(DateTime.now());
    return _records
        .where((r) => r['work_date'] == today && r['status'] == 'REJECTED')
        .length;
  }

  void _snack(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

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

  Future<void> _checkIn() async {
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
      // R-33: penjelasan wajib di luar zona dan saat mengajukan ulang absensi yang ditolak (dicek server juga).
      String? explanation;
      if (outside || _rejectedToday > 0) {
        if (!mounted) return;
        explanation = await _askExplanation(
          title: outside ? 'Absen di luar zona' : 'Ajukan absen ulang',
          info: outside
              ? 'Anda ${distance.round()} m dari ${site['name']} (radius ${radius.round()} m). '
                    'Jelaskan mengapa absen di luar zona.'
              : 'Jelaskan alasan pengajuan ulang absensi yang ditolak.',
        );
        if (explanation == null) return;
      }
      String? selfieId;
      String? faceProbeId;
      File? selfieFile;
      // Pengenalan wajah (karyawan yang sudah mendaftar): dua tantangan acak + gambar wajah sementara. Ini BUKAN
      // foto absensi. Server menghitung cocok/tidak; jaringan putus → lanjut luring (server menandai bila perlu).
      if (_faceEnrolled) {
        if (!mounted) return;
        final face = await captureFaceProbe(context, ref);
        if (face.cancelled) return;
        if (face.error != null) return _snack(face.error!);
        faceProbeId = face.probeId;
      }
      // Foto bukti (swafoto berwatermark) HANYA di luar radius.
      if (outside) {
        if (!mounted) return;
        final (file, err) = await captureWatermarkedPhoto(
          context: context,
          label: 'Swafoto di luar radius',
          kind: LocalFileKind.selfie,
          hint:
              'Anda ${distance.round()} m dari ${site['name']}. Swafoto wajib di luar radius.',
          preferFrontCamera: true,
        );
        if (file == null) {
          if (err != null) _snack(err);
          return;
        }
        selfieFile = file;
      }
      try {
        if (selfieFile != null) {
          selfieId = await ref
              .read(syncEngineProvider)
              .api
              .uploadFile(selfieFile);
        }
        await ref
            .read(syncEngineProvider)
            .api
            .checkIn(
              siteId: site['id'] as String,
              lat: pos.latitude,
              lng: pos.longitude,
              accuracyM: pos.accuracy,
              selfieFileId: selfieId,
              faceProbeId: faceProbeId,
              explanation: explanation,
            );
        _snack('Absen masuk tercatat.');
      } on DioException catch (e) {
        if (!isNetworkFailure(e)) rethrow;
        // R-34: tanpa sinyal → rekam luring bertanda tangan, kirim otomatis saat online.
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
            );
        _snack(
          'Tidak ada sinyal — absen masuk tersimpan luring dan dikirim otomatis saat online.',
        );
      }
      await _load();
    } catch (e) {
      if (!await _handleFaceNotEnrolled(e)) _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _checkOut() async {
    setState(() => _busy = true);
    try {
      final pos = await _position();
      if (pos == null) return;
      // T7: pulang di luar radius lokasi absen masuk → konfirmasi, penjelasan, dan swafoto (tidak masuk galeri).
      // Jarak resmi dihitung ulang server; ini hanya untuk meminta bukti lebih dulu.
      final site = _sites.where((s) => s['id'] == _today?['site_id']).firstOrNull;
      var outside = false;
      var distance = 0.0;
      num radius = 50;
      if (site != null && site['location'] is Map) {
        final loc = site['location'] as Map;
        distance = Geolocator.distanceBetween(
          pos.latitude,
          pos.longitude,
          (loc['lat'] as num).toDouble(),
          (loc['lng'] as num).toDouble(),
        );
        radius = (site['radius_m'] as num?) ?? 50;
        outside = distance > radius;
      }
      String? explanation;
      File? selfieFile;
      if (outside && _today?['status'] != 'OFFLINE') {
        if (!mounted) return;
        explanation = await _askExplanation(
          title: 'Pulang di luar zona',
          info:
              'Anda ${distance.round()} m dari ${site!['name']} (radius ${radius.round()} m). '
              'Jelaskan mengapa pulang di luar zona.',
        );
        if (explanation == null) return;
        if (!mounted) return;
        final (file, err) = await captureWatermarkedPhoto(
          context: context,
          label: 'Swafoto pulang di luar radius',
          kind: LocalFileKind.selfie,
          hint:
              'Anda ${distance.round()} m dari ${site['name']}. Swafoto wajib di luar radius.',
          preferFrontCamera: true,
        );
        if (file == null) {
          if (err != null) _snack(err);
          return;
        }
        selfieFile = file;
      }
      String? faceProbeId;
      // Pulang: hanya pengenalan wajah, TANPA foto bukti.
      if (_faceEnrolled) {
        if (!mounted) return;
        final face = await captureFaceProbe(context, ref);
        if (face.cancelled) return;
        if (face.error != null) return _snack(face.error!);
        faceProbeId = face.probeId;
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
          );
      if (_today?['status'] == 'OFFLINE') {
        await recordOffline();
        _snack(
          'Absen pulang tersimpan luring dan dikirim otomatis saat online.',
        );
      } else {
        try {
          final selfieId = selfieFile == null
              ? null
              : await ref.read(syncEngineProvider).api.uploadFile(selfieFile);
          await ref
              .read(syncEngineProvider)
              .api
              .checkOut(
                lat: pos.latitude,
                lng: pos.longitude,
                accuracyM: pos.accuracy,
                faceProbeId: faceProbeId,
                selfieFileId: selfieId,
                explanation: explanation,
              );
          _snack('Absen pulang tercatat.');
        } on DioException catch (e) {
          if (!isNetworkFailure(e)) rethrow;
          await recordOffline();
          _snack(
            'Tidak ada sinyal — absen pulang tersimpan luring dan dikirim otomatis saat online.',
          );
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
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Daftarkan wajah'),
          ),
        ],
      ),
    );
    ref.invalidate(faceGateProvider);
    return true;
  }

  /// Dialog penjelasan wajib: Kirim dengan isian kosong menampilkan pesan, bukan menutup diam-diam.
  /// Mengembalikan teks (sudah di-trim) atau null bila dibatalkan.
  Future<String?> _askExplanation({
    required String title,
    String? info,
    String initial = '',
  }) {
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
              if (info != null) ...[
                Text(info, style: VmsTextStyles.bodySm),
                const SizedBox(height: 12),
              ],
              TextField(
                key: const Key('explanation-field'),
                controller: controller,
                autofocus: true,
                maxLines: 4,
                maxLength: 1000,
                decoration: InputDecoration(
                  hintText: 'Mis. ban bocor di jalan menuju lokasi',
                  errorText: error,
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Batal'),
            ),
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
    final text = await _askExplanation(
      title: 'Beri penjelasan',
      initial: record['explanation'] as String? ?? '',
    );
    if (text == null) return;
    try {
      await ref
          .read(syncEngineProvider)
          .api
          .explainAttendance(record['id'] as String, text);
      _snack('Penjelasan terkirim.');
      await _load();
    } catch (e) {
      _snack(apiErrorMessage(e));
    }
  }

  String _hhmm(dynamic iso) => iso == null
      ? '--:--'
      : _time.format(DateTime.parse(iso as String).toLocal());

  Widget _timeTile(String label, String value, IconData icon, Accent accent) =>
      Expanded(
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
                  Text(
                    label,
                    style: VmsTextStyles.caption.copyWith(
                      color: Colors.white.withValues(alpha: 0.7),
                    ),
                  ),
                  Text(
                    value,
                    style: VmsTextStyles.title.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      );

  Widget _flag(String text, Accent accent) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(
      color: accent.soft,
      borderRadius: BorderRadius.circular(99),
    ),
    child: Text(
      text,
      style: VmsTextStyles.caption.copyWith(
        color: accent.strong,
        fontWeight: FontWeight.w700,
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    // Sinkron latar selesai (mis. absen luring baru terkirim) → muat ulang kartu & riwayat.
    ref.listen(syncTickProvider, (_, _) => _load());
    ref.listen(liveEventTickProvider, (_, _) => _load());   // T8: peristiwa waktu nyata
    final today = _today;
    final auth = ref.watch(authControllerProvider);
    final name = auth is AuthAuthenticated
        ? auth.user.username.split('@').first
        : '';
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
      appBar: VmsTopBar(
        trailing: HeaderAction(
          icon: Icons.refresh_rounded,
          tooltip: 'Muat ulang',
          onTap: _load,
        ),
      ),
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
                      text:
                          'Luring — data terakhir ${DateFormat('d MMM HH:mm', 'id_ID').format(_cachedAt!)}',
                    ),
                  if (_error != null)
                    NoticeBanner(
                      icon: Icons.error_outline_rounded,
                      text: _error!,
                      accent: Accent.rose,
                    ),
                  FadeSlideIn(
                    child: SurfaceCard(
                      highlight: true,
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            children: [
                              const IconTile(
                                icon: Icons.fingerprint_rounded,
                                accent: Accent.indigo,
                              ),
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
                                      style: VmsTextStyles.bodySm.copyWith(
                                        color: Colors.white.withValues(
                                          alpha: 0.75,
                                        ),
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                              if (today != null)
                                StatusPill(today['status'] as String?),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              _timeTile(
                                'Masuk',
                                _hhmm(today?['check_in_at']),
                                Icons.login_rounded,
                                Accent.emerald,
                              ),
                              const SizedBox(width: 10),
                              _timeTile(
                                'Pulang',
                                _hhmm(today?['check_out_at']),
                                Icons.logout_rounded,
                                Accent.rose,
                              ),
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
                              (today['status'] == 'REJECTED' &&
                                  _rejectedToday < _maxAttemptsPerDay)) ...[
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
                            if (_sites.isEmpty) ...[
                              const NoticeBanner(
                                key: Key('belum-ada-lokasi-sk'),
                                icon: Icons.location_off_rounded,
                                text:
                                    'Belum ada lokasi kerja untuk akun Anda (lokasi rencana kerja maupun kantor). '
                                    'Hubungi Project Manager atau admin untuk menambahkan lokasi kerja.',
                              ),
                              const SizedBox(height: 12),
                            ] else ...[
                              VmsSelectField<String>(
                                label: 'Lokasi kerja',
                                icon: Icons.place_rounded,
                                value: _siteId,
                                options: [
                                  for (final s in _sites)
                                    VmsOption(
                                      s['id'] as String,
                                      s['name'] as String,
                                    ),
                                ],
                                onChanged: (v) => setState(() => _siteId = v),
                              ),
                              const SizedBox(height: 14),
                              // Terikat SK berjalan tetapi memilih lokasi lain (mis. kantor): hanya peringatan,
                              // absen tetap boleh (keputusan pemilik 2026-10-07).
                              if (_runningSites.isNotEmpty &&
                                  _siteId != null &&
                                  !_runningSites.contains(_siteId)) ...[
                                NoticeBanner(
                                  key: const Key('peringatan-bukan-lokasi-sk'),
                                  icon: Icons.warning_amber_rounded,
                                  text:
                                      'Anda sedang bertugas di rencana kerja dengan lokasi '
                                      '${_siteName(_runningSites.first)}. Lokasi yang dipilih bukan lokasi rencana kerja; '
                                      'absen tetap bisa dikirim, tetapi pastikan memang bekerja di sini hari ini.',
                                ),
                                const SizedBox(height: 14),
                              ],
                            ],
                            PrimaryAction(
                              label: today == null
                                  ? 'Absen masuk'
                                  : 'Ajukan absen ulang',
                              icon: Icons.login_rounded,
                              gold: true,
                              busy: _busy,
                              onTap: _loading || _sites.isEmpty
                                  ? null
                                  : _checkIn,
                            ),
                          ] else if ((today['status'] == 'OFFLINE' ||
                                  today['checkout_offline'] == true) &&
                              today['check_out_at'] != null)
                            NoticeBanner(
                              key: const Key('absen-luring-lengkap'),
                              icon: Icons.cloud_upload_rounded,
                              accent: Accent.indigo,
                              text: today['status'] == 'OFFLINE'
                                  ? 'Absen masuk & pulang tersimpan luring. Dikirim '
                                        'otomatis saat ada sinyal.'
                                  : 'Absen pulang tersimpan luring. Dikirim '
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
                          else if (today['check_out_at'] == null &&
                              today['status'] == 'NEEDS_REVIEW')
                            const NoticeBanner(
                              key: Key('pulang-menunggu-review'),
                              icon: Icons.hourglass_top_rounded,
                              text:
                                  'Absen masuk menunggu pemeriksaan. Absen pulang '
                                  'bisa dilakukan setelah absen masuk disetujui.',
                            )
                          else if (today['check_out_at'] == null)
                            PrimaryAction(
                              label: 'Absen pulang',
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
                        ],
                      ),
                    ),
                  ),
                  const SectionTitle('Riwayat'),
                  if (_loading)
                    const Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                  if (!_loading && _records.isEmpty && _error == null)
                    const EmptyState(
                      icon: Icons.event_available_rounded,
                      title: 'Belum ada riwayat absensi',
                    ),
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
                                accent:
                                    r['is_late'] == true ||
                                        r['is_early_leave'] == true
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
                                      _day.format(
                                        DateTime.parse(
                                          r['work_date'] as String,
                                        ),
                                      ),
                                      style: VmsTextStyles.bodySm.copyWith(
                                        fontWeight: FontWeight.w700,
                                        color: VmsColors.neutral900,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      '${_hhmm(r['check_in_at'])} – ${_hhmm(r['check_out_at'])}',
                                      style: VmsTextStyles.bodySm.copyWith(
                                        color: VmsColors.neutral500,
                                      ),
                                    ),
                                    const SizedBox(height: 6),
                                    Wrap(
                                      spacing: 6,
                                      runSpacing: 4,
                                      children: [
                                        if (r['is_late'] == true)
                                          _flag('Terlambat', Accent.amber),
                                        if (r['is_early_leave'] == true)
                                          _flag('Pulang awal', Accent.rose),
                                        if (r['explanation'] != null)
                                          _flag('Dijelaskan', Accent.indigo),
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
                                  child: Text(
                                    r['explanation'] == null
                                        ? 'Jelaskan'
                                        : 'Ubah penjelasan',
                                  ),
                                ),
                            ],
                          ),
                        ),
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

/// Lokasi kerja hari ini sebuah rencana yang berjalan: lokasi khusus hari itu atau lokasi rencana. Null bila bukan
/// rencana berjalan, tidak ada hari kerja hari ini (libur), atau pengguna tidak bertugas hari ini. Data tersimpan
/// lama (tanpa kolom hari ini) memakai lokasi rencana.
String? todaySiteOf(Map<String, dynamic> plan) {
  if (plan['status'] != 'IN_PROGRESS') return null;
  if (!plan.containsKey('today_site_id')) return plan['site_id'] as String?;
  if (plan['today_included'] == false) return null;
  return plan['today_site_id'] as String?;
}
