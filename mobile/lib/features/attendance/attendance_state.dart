part of 'attendance_screen.dart';

/// Bidang dan pembantu kecil state absensi; dipakai bersama mixin pemuat dan aksi.
abstract class _AttendanceBase extends ConsumerState<AttendanceScreen> {
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
}
