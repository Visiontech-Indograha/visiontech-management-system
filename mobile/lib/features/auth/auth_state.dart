/// Cermin dari `RoleCode` di backend (api/app/core/permissions.py) --
/// nilai string HARUS sama persis.
enum UserRole {
  admin('ADMIN'),
  hr('HR'),
  finance('FINANCE'),
  pm('PM'),
  ops('OPS'),
  asset('ASSET'),
  leader('LEADER'),
  member('MEMBER');

  const UserRole(this.wireValue);
  final String wireValue;

  static UserRole fromWire(String value) {
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
  });

  final String id;
  final String username;
  final UserRole role;

  /// Kosong bila akun tidak tertaut ke karyawan (mis. admin murni).
  final String employeeId;

  /// Bentuk `GET /api/v1/auth/me`: user_id, email, role, permissions, employee_id.
  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['user_id'] as String,
      username: json['email'] as String,
      role: UserRole.fromWire(json['role'] as String),
      employeeId: (json['employee_id'] as String?) ?? '',
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
  const AuthUnauthenticated({this.error});
  final String? error;
}
