import 'dart:convert';

import 'package:uuid/uuid.dart';

/// Kunci `Idempotency-Key` untuk SATU niat pengajuan (cuti, mess, pinjam aset, lembur).
///
/// Aturan:
/// - Kunci dibuat (UUID v4) saat pertama kali dikirim, lalu dipakai ulang untuk
///   setiap percobaan ulang selama isi pengajuan tidak berubah. Sinyal putus,
///   timeout, atau 409 IDEMPOTENCY_SEDANG_DIPROSES tidak membuat kunci baru.
/// - Bila isi pengajuan berubah (sidik jari JSON beda), berarti pengajuan baru:
///   kunci baru dibuat. Kunci yang sama dengan isi berbeda akan ditolak server (422).
/// - Setelah berhasil diterima server, [selesai] dipanggil agar pengajuan berikutnya
///   memakai kunci baru.
///
/// Pemegang objek ini harus hidup selama formulir/dialog pengajuan (state layar),
/// bukan dibuat ulang tiap kali tombol ditekan. Endpoint ini tidak punya outbox
/// offline, jadi tidak ada `client_op_id` yang bisa dipakai ulang.
class PengajuanIdempotency {
  static const _uuid = Uuid();

  /// Sama dengan pola server (api/app/api/deps.py): 8 sampai 128 karakter.
  static final pola = RegExp(r'^[A-Za-z0-9._:-]{8,128}$');

  String? _kunci;
  String? _sidikJari;

  /// Kunci untuk [isi] (body permintaan). Dipakai ulang bila isinya sama dengan percobaan sebelumnya.
  String kunciUntuk(Map<String, dynamic> isi) {
    final sidik = jsonEncode(isi);
    if (_kunci == null || _sidikJari != sidik) {
      _kunci = _uuid.v4();
      _sidikJari = sidik;
    }
    return _kunci!;
  }

  /// Pengajuan sudah diterima server (atau ditolak permanen): kunci berikutnya adalah kunci baru.
  void selesai() {
    _kunci = null;
    _sidikJari = null;
  }
}
