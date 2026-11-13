// ignore_for_file: invalid_use_of_protected_member
part of 'attendance_screen.dart';

/// Aksi absen masuk, keluar, bukti, dan penjelasan (dipisah dari berkas utama, perilaku sama).
extension _AttendanceActions on _AttendanceScreenState {
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
      // Layar lain (Jadwal harian) ikut menyegarkan status absen.
      SyncEngine.appliedRevision.value++;
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
                  FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('Tutup dan Selamat Beristirahat')),
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
      // Layar lain (Jadwal harian) ikut menyegarkan status absen.
      SyncEngine.appliedRevision.value++;
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

  String _hhmm(dynamic iso) => iso == null ? '--:--' : _AttendanceScreenState._time.format(DateTime.parse(iso as String).toLocal());

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
}
