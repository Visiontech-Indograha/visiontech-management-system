import 'package:flutter/material.dart';

import '../../core/local_storage.dart';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/location_helper.dart';
import '../../core/photo_capture.dart';
import '../../core/providers.dart';
import '../../data/sync_engine.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_select_field.dart';
import '../../shared/ui/vms_ui.dart';

/// Absensi (M5, dok 05 §3.5). Wajib daring: waktu & geofence ditentukan server.
/// Di luar radius lokasi, server mewajibkan swafoto — aplikasi memintanya lebih dulu.
class AttendanceScreen extends ConsumerStatefulWidget {
  const AttendanceScreen({super.key});

  @override
  ConsumerState<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends ConsumerState<AttendanceScreen> {
  List<Map<String, dynamic>> _records = [];
  String? _serverToday;
  List<Map<String, dynamic>> _sites = [];
  String? _siteId;
  DateTime? _cachedAt;
  bool _loading = true;
  bool _busy = false;
  String? _error;

  static final _day = DateFormat('EEE, d MMM yyyy', 'id_ID');
  static final _time = DateFormat('HH:mm');

  @override
  void initState() {
    super.initState();
    _load();
  }

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
    try {
      final att = await engine.fetchList('attendance', () async {
        final res = await engine.api.myAttendance(employeeId: _employeeId);
        _serverToday = res.today;
        return res.items;
      });
      final sites = await engine.fetchList('sites', engine.api.sites);
      final plans = await engine.fetchList('work_plans', engine.api.workPlans);
      // Titik lokasi SK yang sedang berjalan (ditetapkan PM) didahulukan sebagai lokasi absen.
      final runningSites = [
        for (final p in plans.items)
          if (p['status'] == 'IN_PROGRESS' && p['site_id'] != null)
            p['site_id'] as String,
      ];
      if (!mounted) return;
      setState(() {
        _records = att.items;
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
    for (final r in _records) {
      if (r['check_in_at'] != null &&
          r['check_out_at'] == null &&
          r['status'] != 'REJECTED') {
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
      String? selfieId;
      if (distance > ((site['radius_m'] as num?) ?? 50)) {
        if (!mounted) return;
        final (file, err) = await captureWatermarkedPhoto(
          context: context,
          label: 'Swafoto absen',
          kind: LocalFileKind.selfie,
          hint:
              'Anda ${distance.round()} m dari ${site['name']}. Swafoto wajib di luar radius.',
          preferFrontCamera: true,
        );
        if (file == null) {
          if (err != null) _snack(err);
          return;
        }
        selfieId = await ref.read(syncEngineProvider).api.uploadFile(file);
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
          );
      _snack('Absen masuk tercatat.');
      await _load();
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _checkOut() async {
    setState(() => _busy = true);
    try {
      final pos = await _position();
      if (pos == null) return;
      await ref
          .read(syncEngineProvider)
          .api
          .checkOut(lat: pos.latitude, lng: pos.longitude);
      _snack('Absen pulang tercatat.');
      await _load();
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _explain(Map<String, dynamic> record) async {
    final controller = TextEditingController();
    final text = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Beri penjelasan'),
        content: TextField(
          controller: controller,
          maxLines: 4,
          decoration: const InputDecoration(
            hintText: 'Mis. ban bocor di jalan menuju lokasi',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Kirim'),
          ),
        ],
      ),
    );
    if (text == null || text.isEmpty) return;
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
    final today = _today;
    final auth = ref.watch(authControllerProvider);
    final name = auth is AuthAuthenticated
        ? auth.user.username.split('@').first
        : '';
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
                                          : '${today['site_label']}',
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
                          if (today == null) ...[
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
                            PrimaryAction(
                              label: 'Absen masuk',
                              icon: Icons.login_rounded,
                              gold: true,
                              busy: _busy,
                              onTap: _loading || _sites.isEmpty
                                  ? null
                                  : _checkIn,
                            ),
                          ] else if (today['check_out_at'] == null)
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
                              if ((r['is_late'] == true ||
                                      r['is_early_leave'] == true) &&
                                  r['explanation'] == null)
                                TextButton(
                                  onPressed: () => _explain(r),
                                  child: const Text('Jelaskan'),
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
