/// Cermin dari `RoleCode` di backend (api/app/core/permissions.py) --
/// nilai string HARUS sama persis.
enum UserRole {
  admin('ADMIN'),
  superAdmin('SUPER_ADMIN'),
  hr('HR'),
  finance('FINANCE'),
  pm('PM'),
  ops('OPS'),
  asset('ASSET'),
  leader('LEADER'),
  member('MEMBER');

  const UserRole(this.wireValue);
  final String wireValue;

  /// Peran Master Schema V2 (`users.system_role`) yang dikirim `/auth/me`.
  static const _v2 = {
    'OPERATIONAL_MANAGER': UserRole.ops,
    'PROJECT_MANAGER': UserRole.pm,
    'ADMIN_HR_GA': UserRole.hr,
    'TEAM_LEADER': UserRole.leader,
    'EMPLOYEE': UserRole.member,
  };

  static UserRole fromWire(String? value) {
    final v2 = _v2[value];
    if (v2 != null) return v2;
    return UserRole.values.firstWhere(
      (r) => r.wireValue == value,
      orElse: () => UserRole.member,
    );
  }
}

class AuthUser {
  const AuthUser({
    required this.id,
    required this.username,
    required this.role,
    required this.employeeId,
    this.attendanceMode = 'FIELD',
    this.photoFileId,
    this.fullName,
    this.mustChangePassword = false,
  });

  /// True bila sandi sementara dari admin belum diganti: aplikasi hanya boleh membuka layar Ganti sandi.
  final bool mustChangePassword;

  AuthUser withMustChange(bool value) => AuthUser(
    id: id,
    username: username,
    role: role,
    employeeId: employeeId,
    attendanceMode: attendanceMode,
    photoFileId: photoFileId,
    fullName: fullName,
    mustChangePassword: value,
  );

  final String id;
  final String username;
  final UserRole role;

  /// Kosong bila akun tidak tertaut ke karyawan (mis. admin murni).
  final String employeeId;

  /// `FIELD` = pekerja lapangan (absen di HP), `OFFICE` = pekerja kantor (absen di web).
  /// Server tetap menolak kanal yang salah; nilai ini hanya untuk tampilan.
  final String attendanceMode;

  /// ID berkas foto profil karyawan; null bila belum ada. URL bertanda tangan
  /// diambil lewat `GET /files/{id}/url` (lihat VmsApi.fileUrl).
  final String? photoFileId;

  /// Nama lengkap karyawan (dari `/auth/me`); null bila akun belum tertaut ke karyawan.
  final String? fullName;

  /// Nama untuk tampilan: nama lengkap, atau bagian depan email bila belum ada.
  String get displayName {
    final n = fullName?.trim();
    return (n != null && n.isNotEmpty) ? n : username.split('@').first;
  }

  /// Administrator (pemilik sistem) boleh absen dari HP maupun web, jadi tidak diarahkan ke web saja.
  bool get absensiLewatWeb =>
      attendanceMode == 'OFFICE' && role != UserRole.admin && role != UserRole.superAdmin;

  /// Bentuk `GET /api/v1/auth/me`: user_id, email, role, permissions, employee_id,
  /// attendance_mode, photo_file_id.
  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: (json['user_id'] as String?) ?? '',
      username: (json['email'] as String?) ?? '',
      role: UserRole.fromWire(json['role'] as String?),
      employeeId: (json['employee_id'] as String?) ?? '',
      attendanceMode: (json['attendance_mode'] as String?) ?? 'FIELD',
      photoFileId: json['photo_file_id'] as String?,
      fullName: json['full_name'] as String?,
      mustChangePassword: json['must_change_password'] == true,
    );
  }
}

sealed class AuthState {
  const AuthState();
}

/// Status awal sebelum sesi tersimpan selesai dicek.
class AuthInitial extends AuthState {
  const AuthInitial();
}

class AuthLoading extends AuthState {
  const AuthLoading();
}

class AuthAuthenticated extends AuthState {
  const AuthAuthenticated(this.user);
  final AuthUser user;
}

/// Sesi SUDAH sah (token tervalidasi/direstore) tapi masih menunggu unlock
/// sidik jari lokal sebelum konten aplikasi ditampilkan -- lihat plan
/// Keputusan 7. Beda dari AuthAuthenticated: otorisasi ke server tidak
/// berubah sama sekali, ini murni gerbang LOKAL di HP.
class AuthLocked extends AuthState {
  const AuthLocked(this.user);
  final AuthUser user;
}

class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated({this.error, this.lockedUntil});
  final String? error;

  /// Terisi bila server mengunci login sementara (5 kali gagal / 15 menit,
  /// R-21) -- tombol Masuk dimatikan dan hitung mundur ditampilkan sampai jam ini.
  final DateTime? lockedUntil;
}
