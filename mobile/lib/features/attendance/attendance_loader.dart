// ignore_for_file: invalid_use_of_protected_member
part of 'attendance_screen.dart';

/// Pemuatan data, lokasi, dan pengingat layar absensi (dipisah dari berkas utama, perilaku sama).
extension _AttendanceLoader on _AttendanceScreenState {
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
              attendanceClock().toUtc().add(const Duration(hours: 7)));
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
        final authNow = ref.read(authControllerProvider);
        final ownOffice = authNow is AuthAuthenticated ? authNow.user.officeId : null;
        _sites = [...daySites, ...ownOfficeFirst(sites.items, ownOffice)];
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
          // Tanpa GPS: lokasi absen terakhir pengguna sendiri, baru urutan abjad (bukan kantor acak).
          final lastId = att.items.map((r) => r['site_id']).whereType<String>().firstOrNull;
          final last = lastId != null && _sites.any((s) => s['id'] == lastId) ? lastId : null;
          _siteId = defaultSiteId(_sites, near: near, last: last, ownOfficeId: ownOffice);
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
    final current = _serverToday ?? DateFormat('yyyy-MM-dd').format(attendanceClock());
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
    final dayNow = _serverToday ?? DateFormat('yyyy-MM-dd').format(attendanceClock());
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
    final today = _serverToday ?? DateFormat('yyyy-MM-dd').format(attendanceClock());
    for (final r in _records) {
      if (r['work_date'] == today) return r;
    }
    return null;
  }

  int get _rejectedToday {
    final today = _serverToday ?? DateFormat('yyyy-MM-dd').format(attendanceClock());
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
      _snack(mockLocationMessage);
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
}
