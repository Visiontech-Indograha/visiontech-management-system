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
import '../dokumen/dokumen_kendaraan.dart';
import '../face/face_enroll_gate.dart';
import '../notifications/notifications_screen.dart' show NotificationBell;
import '../plans/daily_plan_screen.dart';
import 'nearest_site.dart';
import 'session_labels.dart';

part 'attendance_actions.dart';
part 'attendance_helpers.dart';
part 'attendance_loader.dart';

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

  /// Keputusan pemilik 2026-10-02: ditolak → boleh mengajukan ulang sekali; ditolak lagi →
  /// hari itu terkunci dan tercatat ditolak (server menolak dengan ATTENDANCE_DAY_LOCKED).
  static const _maxAttemptsPerDay = 2;

  Map<String, int> _summary = const {};
  bool _siteManual = false; // pengguna memilih lokasi sendiri → jangan diganti otomatis

  @override
  Widget build(BuildContext context) {
    // Sinkron latar selesai (mis. absen offline baru terkirim) → muat ulang kartu & riwayat.
    ref.listen(syncTickProvider, (_, _) => _load());
    ref.listen(liveEventTickProvider, (_, _) => _load()); // T8: peristiwa waktu nyata
    final today = _today;
    final auth = ref.watch(authControllerProvider);
    final name = auth is AuthAuthenticated ? auth.user.displayName.split(' ').first : '';
    final lewatWeb = auth is AuthAuthenticated && auth.user.absensiLewatWeb;
    final hour = attendanceClock().hour;
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
              subtitle: _day.format(attendanceClock()),
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
                  const DokumenPengingatBanner(),
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
                                  ? 'Absen masuk dan pulang tersimpan offline. Dikirim '
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
