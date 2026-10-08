import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/error_message.dart';
import '../../core/local_storage.dart';
import '../../core/photo_capture.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../data/sync_engine.dart';
import '../../shared/ui/vms_select_field.dart';
import '../../shared/ui/vms_ui.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import 'photo_slots.dart';
import 'sk_viewer_screen.dart';

/// Satu hari kerja SK: checklist tugas + laporan harian (dok 05 §3.7). Ketua SK
/// mengisi & mengirim; semua aksi lewat antrean luring (idempoten per client_op_id).
class PlanDayScreen extends ConsumerStatefulWidget {
  const PlanDayScreen({
    super.key,
    required this.planId,
    required this.day,
    required this.canEdit,
    this.isLeader = false,
    this.running = false,
  });
  final String planId;
  final Map<String, dynamic> day;
  final bool canEdit;

  /// Alur SK v2: ketua menghimpun laporan anggota; anggota mengirim laporannya ke ketua.
  final bool isLeader;
  final bool running;

  @override
  ConsumerState<PlanDayScreen> createState() => _PlanDayScreenState();
}

class _PlanDayScreenState extends ConsumerState<PlanDayScreen> {
  late final List<Map<String, dynamic>> _tasks = (widget.day['tasks'] as List)
      .map((t) => Map<String, dynamic>.from(t as Map))
      .toList();
  late final Map<String, dynamic>? _report = widget.day['report'] == null
      ? null
      : Map<String, dynamic>.from(widget.day['report'] as Map);
  late final _body = TextEditingController(
    text: _report?['body'] as String? ?? '',
  );
  late final _obstacle = TextEditingController(
    text: _report?['obstacle'] as String? ?? '',
  );
  final List<PendingPhoto> _pending = [];
  bool _busy = false;
  List<Map<String, dynamic>> _template = [];   // T9: template foto laporan

  // Laporan anggota (alur SK v2 PR2).
  List<Map<String, dynamic>> _memberReports = [];
  Map<String, dynamic>? _mine;
  final _mBody = TextEditingController();
  final _mObstacle = TextEditingController();
  final List<PendingPhoto> _mPending = [];
  bool _mBusy = false;

  @override
  void initState() {
    super.initState();
    _loadMembers();
  }

  Future<void> _loadMembers() async {
    final api = ref.read(syncEngineProvider).api;
    try {
      final template = await api.photoTemplate(widget.planId);
      if (mounted) setState(() => _template = template);
    } catch (_) {
      // Luring: tanpa template, hanya "Foto lain".
    }
    try {
      if (widget.isLeader) {
        final list = await api.memberReports(widget.planId, _dayId);
        if (mounted) setState(() => _memberReports = list);
      } else if (widget.running) {
        final mine = await api.myMemberReport(widget.planId, _dayId);
        if (mounted) {
          setState(() {
            _mine = mine;
            _mBody.text = mine?['body'] as String? ?? '';
            _mObstacle.text = mine?['obstacle'] as String? ?? '';
          });
        }
      }
    } catch (_) {
      // Luring: bagian laporan anggota tidak ditampilkan.
    }
  }

  /// Ketua: susun uraian & kendala dari laporan anggota yang sudah dikirim (bisa diedit setelahnya).
  void _compile() {
    final sent = _memberReports.where((m) => m['status'] == 'SENT').toList();
    if (sent.isEmpty) return _snack('Belum ada laporan anggota yang dikirim.');
    _body.text = sent.map((m) => '${m['full_name']}: ${m['body']}').join('\n');
    final obstacles = sent
        .where((m) => '${m['obstacle']}'.trim().isNotEmpty)
        .map((m) => '${m['full_name']}: ${m['obstacle']}')
        .toList();
    _obstacle.text = obstacles.isEmpty ? 'Tidak ada' : obstacles.join('\n');
    _snack(
      'Uraian disusun dari ${sent.length} laporan anggota. Silakan periksa sebelum dikirim.',
    );
  }

  Future<void> _memberPhoto(String? slot, PhotoOrigin origin) async {
    final photo = await pickReportPhoto(
      context: context,
      slot: slot,
      origin: origin,
      hint: 'Foto hasil pekerjaan Anda hari ini',
      onError: _snack,
    );
    if (photo != null && mounted) setState(() => _mPending.add(photo));
  }

  void _dropMemberPhoto(PendingPhoto photo) => setState(() => _mPending.remove(photo));

  void _dropPhoto(PendingPhoto photo) => setState(() => _pending.remove(photo));

  List<Map<String, dynamic>> _evidenceOf(Map<String, dynamic>? report) =>
      ((report?['evidence'] as List?) ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();

  Future<void> _memberSave({required bool send}) async {
    if (_mBody.text.trim().length < 10) {
      return _snack('Uraian laporan minimal 10 karakter.');
    }
    final missing = PhotoSlots.missingRequired(_template, _evidenceOf(_mine), _mPending);
    if (send && missing.isNotEmpty) {
      return _snack('Foto wajib belum lengkap: ${missing.join(', ')}.');
    }
    setState(() => _mBusy = true);
    final api = ref.read(syncEngineProvider).api;
    try {
      final evidence = _evidenceOf(_mine);
      for (final p in _mPending) {
        evidence.add({
          'file_id': await api.uploadFile(File(p.path)),
          'slot_label': p.slot,
          'source': p.source,
        });
      }
      var mine = await api.saveMemberReport(
        widget.planId,
        _dayId,
        body: _mBody.text.trim(),
        obstacle: _mObstacle.text.trim(),
        evidenceFileIds: const [],
        evidence: evidence,
      );
      _mPending.clear();
      if (send) mine = await api.sendMemberReport(widget.planId, _dayId);
      if (!mounted) return;
      setState(() => _mine = mine);
      _snack(send ? 'Laporan dikirim ke ketua tim.' : 'Draf laporan disimpan.');
    } catch (e) {
      if (mounted) _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _mBusy = false);
    }
  }

  String get _dayId => widget.day['id'] as String;
  String get _status => (_report?['status'] as String?) ?? 'DRAFT';
  String get _badge => _status == 'SUBMITTED' && _report?['resubmitted'] == true
      ? 'RESUBMITTED'
      : _status;
  bool get _editable =>
      widget.canEdit && (_status == 'DRAFT' || _status == 'CHANGES_REQUESTED');

  void _snack(String m) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  /// Daftar anggota khusus hari ini (termasuk ketua); null = seluruh tim bertugas.
  bool get _offDuty {
    final ids = widget.day['member_employee_ids'];
    if (widget.isLeader || ids is! List) return false;
    final auth = ref.read(authControllerProvider);
    return auth is AuthAuthenticated && !ids.contains(auth.user.employeeId);
  }

  Future<bool> _send(
    String op,
    Map<String, dynamic> payload, {
    List<String> files = const [],
  }) async {
    try {
      final sent = await ref
          .read(syncEngineProvider)
          .submit(op, payload, localFiles: files);
      _snack(
        sent
            ? 'Terkirim.'
            : 'Tersimpan di HP, dikirim otomatis saat ada sinyal.',
      );
      return true;
    } on SyncRejectedException catch (e) {
      _snack(e.message);
    } catch (e) {
      _snack(apiErrorMessage(e));
    }
    return false;
  }

  Future<void> _toggle(Map<String, dynamic> task) async {
    setState(() => task['is_done'] = !(task['is_done'] == true));
    final ok = await _send(OfflineOp.taskToggle, {
      'plan_id': widget.planId,
      'day_id': _dayId,
      'task_id': task['id'],
    });
    if (!ok && mounted) {
      setState(() => task['is_done'] = !(task['is_done'] == true));
    }
  }

  Future<void> _addPhoto(String? slot, PhotoOrigin origin) async {
    final photo = await pickReportPhoto(
      context: context,
      slot: slot,
      origin: origin,
      onError: _snack,
    );
    if (photo != null && mounted) setState(() => _pending.add(photo));
  }

  Future<void> _save({required bool submit}) async {
    if (_body.text.trim().isEmpty) {
      return _snack('Isi uraian pekerjaan hari ini.');
    }
    if (submit && _body.text.trim().length < 10) {
      // Draf boleh pendek, tetapi laporan yang dikirim ke PM minimal 10 karakter (server menolak yang lebih pendek).
      return _snack('Uraian pekerjaan minimal 10 karakter sebelum dikirim.');
    }
    final missing = PhotoSlots.missingRequired(_template, _evidenceOf(_report), _pending);
    if (submit && missing.isNotEmpty) {
      return _snack('Foto wajib belum lengkap: ${missing.join(', ')}.');
    }
    setState(() => _busy = true);
    final base = {'plan_id': widget.planId, 'day_id': _dayId};
    // T9: foto berlabel slot diunggah langsung (butuh sinyal) agar slot + sumbernya ikut tersimpan; tanpa sinyal,
    // foto masuk antrean luring tanpa label (server akan menolak kirim bila slot wajib kosong).
    final evidence = _evidenceOf(_report);
    var queueFiles = <String>[];
    try {
      final api = ref.read(syncEngineProvider).api;
      for (final p in _pending) {
        evidence.add({
          'file_id': await api.uploadFile(File(p.path)),
          'slot_label': p.slot,
          'source': p.source,
        });
      }
    } catch (_) {
      queueFiles = _pending.map((p) => p.path).toList();
    }
    final saved = await _send(OfflineOp.dailyReportSave, {
      ...base,
      'body': _body.text.trim(),
      'obstacle': _obstacle.text.trim(),
      'evidence_file_ids': List<String>.from(
        (_report?['evidence_file_ids'] as List?) ?? const [],
      ),
      'evidence': evidence,
    }, files: queueFiles);
    if (saved) _pending.clear();
    final submitted =
        saved && submit && await _send(OfflineOp.dailyReportSubmit, base);
    if (mounted) {
      setState(() => _busy = false);
      // Layar hanya ditutup bila pengiriman ke PM berhasil (CELAH 9, docs/28).
      if (submitted) Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final done = _tasks.where((t) => t['is_done'] == true).length;
    final saved = ((_report?['evidence_file_ids'] as List?) ?? const []).length;
    return Scaffold(
      appBar: VmsTopBar(onBack: () => Navigator.of(context).maybePop()),
      body: ListView(
        padding: safeListPadding(context),
        children: [
          HeroHeader(
            eyebrow: 'Hari kerja',
            title: '${widget.day['title']}',
            subtitle: '$done dari ${_tasks.length} tugas selesai',
            bottom: StatusPill(
              widget.isLeader || _mine == null ? _badge : '${_mine!['status']}',
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (widget.day['site_name'] != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: SurfaceCard(
                      key: const Key('day-site'),
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        children: [
                          const Icon(Icons.place_outlined),
                          const SizedBox(width: 8),
                          Expanded(child: Text('Lokasi hari ini: ${widget.day['site_name']}')),
                        ],
                      ),
                    ),
                  ),
                if (_offDuty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: SurfaceCard(
                      key: const Key('day-off-duty'),
                      padding: const EdgeInsets.all(12),
                      child: Text(
                        'Anda tidak ditugaskan pada hari ini. Tidak perlu absen dan membuat laporan; Anda tetap tercatat sebagai anggota rencana kerja.',
                        style: VmsTextStyles.bodySm,
                      ),
                    ),
                  ),
                const SectionTitle('Tugas'),
                if (_tasks.isEmpty)
                  const EmptyState(
                    icon: Icons.checklist_rounded,
                    title: 'Belum ada tugas untuk hari ini',
                  ),
                for (final (i, t) in _tasks.indexed)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: FadeSlideIn(
                      index: i,
                      child: SurfaceCard(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                        onTap: widget.canEdit ? () => _toggle(t) : null,
                        child: Row(
                          children: [
                            AnimatedContainer(
                              duration: const Duration(milliseconds: 220),
                              width: 26,
                              height: 26,
                              decoration: BoxDecoration(
                                color: t['is_done'] == true
                                    ? Accent.emerald.strong
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                  color: t['is_done'] == true
                                      ? Accent.emerald.strong
                                      : VmsColors.neutral300,
                                  width: 2,
                                ),
                              ),
                              child: t['is_done'] == true
                                  ? const Icon(
                                      Icons.check_rounded,
                                      size: 18,
                                      color: Colors.white,
                                    )
                                  : null,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                '${t['title']}',
                                style: VmsTextStyles.bodySm.copyWith(
                                  fontWeight: FontWeight.w600,
                                  color: t['is_done'] == true
                                      ? VmsColors.neutral500
                                      : VmsColors.neutral900,
                                  decoration: t['is_done'] == true
                                      ? TextDecoration.lineThrough
                                      : null,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                if (!widget.isLeader && widget.running && !_offDuty) ..._memberSection(),
                if (widget.isLeader && _memberReports.isNotEmpty)
                  ..._leaderMembersSection(),
                const SectionTitle('Laporan harian'),
                if (_status == 'APPROVED')
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: OutlinedButton.icon(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => SkViewerScreen(
                            planId: widget.planId,
                            title:
                                'Laporan harian · ${widget.day['work_date']}',
                            htmlPath:
                                '/work-plans/${widget.planId}/days/$_dayId/report/html',
                          ),
                        ),
                      ),
                      icon: const Icon(Icons.description_outlined),
                      label: const Text('Lihat laporan (disetujui PM)'),
                    ),
                  ),
                if (_report?['review_note'] != null)
                  NoticeBanner(
                    icon: Icons.rate_review_rounded,
                    text: 'Catatan PM: ${_report!['review_note']}',
                    accent: Accent.rose,
                  ),
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextField(
                        controller: _body,
                        enabled: _editable,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          labelText: 'Uraian pekerjaan',
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _obstacle,
                        enabled: _editable,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: 'Kendala (boleh kosong)',
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        '$saved foto tersimpan${_pending.isEmpty ? '' : ' · ${_pending.length} baru'}',
                        style: VmsTextStyles.bodySm.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 8),
                      PhotoSlots(
                        template: _template,
                        saved: _evidenceOf(_report),
                        pending: _pending,
                        enabled: _editable,
                        onAdd: _addPhoto,
                        onRemove: _dropPhoto,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                if (_editable) ...[
                  PrimaryAction(
                    label: 'Kirim ke PM',
                    icon: Icons.send_rounded,
                    busy: _busy,
                    onTap: () => _save(submit: true),
                  ),
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed: _busy ? null : () => _save(submit: false),
                    icon: const Icon(Icons.save_rounded),
                    label: const Text('Simpan draf'),
                  ),
                ] else if (!widget.canEdit)
                  const NoticeBanner(
                    icon: Icons.info_outline_rounded,
                    text:
                        'Hanya ketua rencana kerja yang mengisi laporan saat rencana kerja berjalan.',
                    accent: Accent.blue,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

extension on _PlanDayScreenState {
  List<Widget> _leaderMembersSection() => [
    SectionTitle(
      'Laporan anggota (${_memberReports.where((m) => m['status'] == 'SENT').length})',
    ),
    for (final m in _memberReports)
      Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: SurfaceCard(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      '${m['full_name']} — ${m['position']}',
                      style: VmsTextStyles.bodySm.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  StatusPill(m['status'] == 'SENT' ? 'SENT' : 'DRAFT'),
                ],
              ),
              const SizedBox(height: 4),
              Text('${m['body']}', style: VmsTextStyles.bodySm),
              if ('${m['obstacle']}'.isNotEmpty)
                Text('Kendala: ${m['obstacle']}', style: VmsTextStyles.caption),
            ],
          ),
        ),
      ),
    if (_editable)
      OutlinedButton.icon(
        key: const Key('compile-member-reports'),
        onPressed: _compile,
        icon: const Icon(Icons.merge_type_rounded),
        label: const Text('Susun dari laporan anggota'),
      ),
  ];

  List<Widget> _memberSection() {
    final sent = _mine?['status'] == 'SENT';
    final savedPhotos =
        ((_mine?['evidence_file_ids'] as List?) ?? const []).length;
    return [
      const SectionTitle('Laporan saya untuk ketua'),
      if (sent)
        const NoticeBanner(
          icon: Icons.check_circle_outline_rounded,
          text: 'Laporan Anda sudah dikirim ke ketua tim.',
          accent: Accent.emerald,
        ),
      SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              key: const Key('member-report-body'),
              controller: _mBody,
              enabled: !sent,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Uraian pekerjaan saya',
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _mObstacle,
              enabled: !sent,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Kendala (boleh kosong)',
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              '$savedPhotos foto tersimpan${_mPending.isEmpty ? '' : ' · ${_mPending.length} baru'}',
              style: VmsTextStyles.bodySm,
            ),
            const SizedBox(height: 8),
            PhotoSlots(
              template: _template,
              saved: _evidenceOf(_mine),
              pending: _mPending,
              enabled: !sent,
              onAdd: _memberPhoto,
              onRemove: _dropMemberPhoto,
            ),
          ],
        ),
      ),
      const SizedBox(height: 12),
      if (!sent) ...[
        PrimaryAction(
          label: 'Kirim ke ketua',
          icon: Icons.send_rounded,
          busy: _mBusy,
          onTap: () => _memberSave(send: true),
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: _mBusy ? null : () => _memberSave(send: false),
          icon: const Icon(Icons.save_rounded),
          label: const Text('Simpan draf'),
        ),
      ],
      const SizedBox(height: 16),
    ];
  }
}

/// Form insiden K3/aset (dok 05 §3.9). Mengembalikan data + path foto lokal.
class IncidentFormScreen extends StatefulWidget {
  const IncidentFormScreen({super.key});

  @override
  State<IncidentFormScreen> createState() => _IncidentFormScreenState();
}

class _IncidentFormScreenState extends State<IncidentFormScreen> {
  static const _categories = {
    'K3_RINGAN': 'K3 ringan',
    'K3_BERAT': 'K3 berat',
    'K3_LINGKUNGAN': 'K3 lingkungan',
    'K3_HAMPIR': 'Hampir celaka',
    'ASET': 'Kerusakan aset',
  };
  static const _severities = {
    'RENDAH': 'Rendah',
    'SEDANG': 'Sedang',
    'TINGGI': 'Tinggi',
    'KRITIS': 'Kritis',
  };

  String _category = 'K3_RINGAN';
  String _severity = 'RENDAH';
  final _description = TextEditingController();
  final List<String> _photos = [];

  Future<void> _addPhoto() async {
    final (file, err) = await captureWatermarkedPhoto(
      context: context,
      label: 'Foto insiden',
      hint: 'Foto lokasi kejadian',
      kind: LocalFileKind.incident,
    );
    if (file != null) setState(() => _photos.add(file.path));
    if (err != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: VmsTopBar(onBack: () => Navigator.of(context).maybePop()),
      body: ListView(
        padding: safeListPadding(context),
        children: [
          const HeroHeader(
            eyebrow: 'K3 & aset',
            title: 'Lapor insiden',
            subtitle: 'Foto berwatermark GPS & waktu, tersimpan di HP bila tanpa sinyal.',
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      VmsSelectField<String>(
                        label: 'Kategori',
                        icon: Icons.category_rounded,
                        value: _category,
                        options: [
                          for (final e in _categories.entries)
                            VmsOption(e.key, e.value),
                        ],
                        onChanged: (v) => setState(() => _category = v),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Tingkat keparahan',
                        style: VmsTextStyles.caption.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final e in _severities.entries)
                            Pressable(
                              onTap: () => setState(() => _severity = e.key),
                              child: AnimatedContainer(
                                duration: const Duration(milliseconds: 200),
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 14,
                                  vertical: 8,
                                ),
                                decoration: BoxDecoration(
                                  color: _severity == e.key
                                      ? _severityAccent(e.key).strong
                                      : _severityAccent(e.key).soft,
                                  borderRadius: BorderRadius.circular(99),
                                ),
                                child: Text(
                                  e.value,
                                  style: VmsTextStyles.bodySm.copyWith(
                                    fontWeight: FontWeight.w700,
                                    color: _severity == e.key
                                        ? Colors.white
                                        : _severityAccent(e.key).strong,
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      TextField(
                        controller: _description,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          labelText: 'Kronologi',
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          const IconTile(
                            icon: Icons.photo_camera_rounded,
                            accent: Accent.rose,
                            size: 40,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              '${_photos.length} foto bukti',
                              style: VmsTextStyles.bodySm.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          TextButton.icon(
                            onPressed: _addPhoto,
                            icon: const Icon(Icons.add_a_photo_rounded),
                            label: const Text('Foto'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                PrimaryAction(
                  label: 'Kirim laporan',
                  icon: Icons.send_rounded,
                  accent: Accent.rose,
                  onTap: () {
                    if (_description.text.trim().isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Isi kronologi kejadian.'),
                        ),
                      );
                      return;
                    }
                    Navigator.of(context).pop(<String, dynamic>{
                      'category': _category,
                      'severity': _severity,
                      'description': _description.text.trim(),
                      'files': _photos,
                    });
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Accent _severityAccent(String key) => switch (key) {
    'RENDAH' => Accent.emerald,
    'SEDANG' => Accent.amber,
    'TINGGI' => Accent.rose,
    _ => Accent.violet,
  };
}
