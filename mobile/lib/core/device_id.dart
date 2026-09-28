import 'package:uuid/uuid.dart';

import 'token_storage.dart';

/// client_id yang dikirim saat login (WAJIB untuk role FIELD_STAFF, lihat
/// Keputusan 2 di plan). Backend hanya butuh string yang STABIL per-install,
/// bukan identifier hardware sungguhan -- jadi UUID acak yang dibuat sekali
/// lalu disimpan di secure storage sudah cukup & lebih tahan terhadap
/// pembatasan privasi Android (device_info_plus tidak punya cara yang andal
/// memberi ID perangkat sungguhan sejak Android 10+).
///
/// Reinstall app akan menghasilkan client_id baru -- ini sesuai desain:
/// backend akan menolak login (403 "terikat dengan perangkat lain") sampai
/// HR mereset device_id akun tsb, cermin dari kondisi HP benar-benar berganti.
class DeviceIdProvider {
  const DeviceIdProvider(this._tokenStorage);

  final TokenStorage _tokenStorage;

  Future<String> getClientId() async {
    final cached = await _tokenStorage.readClientId();
    if (cached != null && cached.isNotEmpty) return cached;

    final generated = const Uuid().v4();
    await _tokenStorage.saveClientId(generated);
    return generated;
  }
}
