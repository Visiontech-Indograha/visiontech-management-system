import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';
import 'auth_controller.dart';
import 'auth_state.dart';

/// Peran kantor: aplikasi HP hanya melayani alur lapangan (absensi, surat
/// kerja, profil), pekerjaan peran ini ada di web (R-21, keputusan pemilik: opsi a).
const _officeRoleWork = {
  UserRole.admin: 'Pengaturan akun & organisasi',
  UserRole.hr: 'Karyawan, akun, dan dokumen kepegawaian',
  UserRole.finance: 'Lembur dan keuangan',
  UserRole.ops: 'Pantauan operasional',
  UserRole.asset: 'Aset dan serah terima',
  UserRole.pm: 'Terbitkan SK, persetujuan, dan pantauan tim',
};

bool isOfficeRole(UserRole role) => _officeRoleWork.containsKey(role);

/// Kartu penanda untuk peran kantor. PM mendapat label "Segera hadir"
/// karena menu PM di HP memang direncanakan (R-09, desain ditunda).
/// Tidak tampil untuk anggota/ketua lapangan.
class OfficeRoleNotice extends ConsumerWidget {
  const OfficeRoleNotice({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final role = auth is AuthAuthenticated ? auth.user.role : null;
    if (role == null || !isOfficeRole(role)) return const SizedBox.shrink();
    final isPm = role == UserRole.pm;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: SurfaceCard(
        key: const Key('office-role-notice'),
        accent: isPm ? VmsColors.gold : Accent.blue.strong,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    isPm ? 'Menu Project Manager' : 'Akun kantor',
                    style: VmsTextStyles.body.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                if (isPm)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: Accent.amber.soft,
                      borderRadius: BorderRadius.circular(99),
                    ),
                    child: Text(
                      'Segera hadir',
                      style: VmsTextStyles.caption.copyWith(
                        color: Accent.amber.strong,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              isPm
                  ? '${_officeRoleWork[role]} di HP sedang disiapkan. Untuk '
                        'sementara kerjakan lewat web. Di HP Anda tetap bisa '
                        'absen dan melihat surat kerja sebagai karyawan.'
                  : '${_officeRoleWork[role]} dikerjakan lewat web. Di HP '
                        'Anda tetap bisa absen dan melihat surat kerja sebagai '
                        'karyawan.',
              style: VmsTextStyles.bodySm.copyWith(color: VmsColors.neutral700),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Text(
                    ApiConfig.baseUrl,
                    style: VmsTextStyles.caption.copyWith(
                      color: VmsColors.brand700,
                      fontWeight: FontWeight.w700,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                TextButton.icon(
                  onPressed: () async {
                    await Clipboard.setData(
                      const ClipboardData(text: ApiConfig.baseUrl),
                    );
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Alamat web disalin.')),
                      );
                    }
                  },
                  icon: const Icon(Icons.copy_rounded, size: 16),
                  label: const Text('Salin alamat web'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
