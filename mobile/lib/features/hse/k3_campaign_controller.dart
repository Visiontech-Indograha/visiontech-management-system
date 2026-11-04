import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import '../../data/vms_api.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import 'k3_campaign.dart';

/// Klien API untuk popup K3 (API yang sama dipakai web).
final k3ApiProvider = Provider<VmsApi>((ref) => VmsApi(ref.watch(apiClientProvider)));

const k3NetworkMessage = 'Belum terkirim karena tidak ada koneksi. Periksa jaringan, lalu tekan Coba lagi.';
const k3ErrorMessage = 'Gagal mengonfirmasi. Coba lagi.';

class K3State {
  const K3State({this.campaign, this.sending = false, this.error, this.pendingReadSeconds});

  /// Kampanye yang wajib dibaca sekarang; null bila tidak ada.
  final K3Campaign? campaign;
  final bool sending;

  /// Pesan galat konfirmasi terakhir; null bila tidak ada.
  final String? error;

  /// Durasi baca yang belum berhasil dikirim (dicoba lagi saat online).
  final int? pendingReadSeconds;
}

/// Mengambil kampanye K3 wajib yang belum dikonfirmasi, dan mengirim konfirmasinya.
/// Galat jaringan saat mengambil TIDAK ditampilkan: aplikasi tetap bisa dipakai (termasuk absensi offline).
class K3CampaignController extends Notifier<K3State> {
  bool _checking = false;

  @override
  K3State build() => const K3State();

  /// Cek kampanye baru. Dilewati bila sudah ada yang ditampilkan, sedang memeriksa, belum login, atau offline.
  Future<void> check() async {
    if (_checking || state.campaign != null) return;
    if (ref.read(authControllerProvider) is! AuthAuthenticated) return;
    if (NetworkHint.probablyOffline) return;
    _checking = true;
    try {
      final json = await ref.read(k3ApiProvider).activeK3Popup();
      final raw = json['campaign'];
      if (raw is! Map) return;
      final campaign = K3Campaign.fromJson(Map<String, dynamic>.from(raw));
      state = K3State(campaign: campaign);
      // Penanda "sudah tampil" hanya untuk statistik server; galatnya tidak perlu diketahui pengguna.
      unawaited(ref.read(k3ApiProvider).markK3Seen(campaign.id).catchError((Object _) {}));
    } catch (_) {
      // Diam-diam: dicoba lagi saat aplikasi kembali ke depan atau saat online.
    } finally {
      _checking = false;
    }
  }

  /// Kirim konfirmasi baca. Berhasil → kampanye dilepas dari layar.
  Future<void> confirm(int readSeconds) async {
    final campaign = state.campaign;
    if (campaign == null || state.sending) return;
    state = K3State(campaign: campaign, sending: true, pendingReadSeconds: readSeconds);
    try {
      await ref.read(k3ApiProvider).acknowledgeK3(campaign.id, readSeconds, 'Aplikasi HP');
      state = const K3State();
    } on DioException catch (e) {
      state = K3State(
        campaign: campaign,
        error: isNetworkFailure(e) ? k3NetworkMessage : k3ErrorMessage,
        pendingReadSeconds: readSeconds,
      );
    } catch (_) {
      state = K3State(campaign: campaign, error: k3ErrorMessage, pendingReadSeconds: readSeconds);
    }
  }

  /// Coba lagi konfirmasi yang belum terkirim (dipanggil saat tombol Coba lagi atau aplikasi kembali ke depan).
  Future<void> retryPending() async {
    final pending = state.pendingReadSeconds;
    if (pending == null || state.campaign == null || state.sending) return;
    await confirm(pending);
  }

  /// Lepas kampanye (mis. saat keluar akun).
  void reset() {
    state = const K3State();
  }
}

final k3CampaignProvider = NotifierProvider<K3CampaignController, K3State>(K3CampaignController.new);
