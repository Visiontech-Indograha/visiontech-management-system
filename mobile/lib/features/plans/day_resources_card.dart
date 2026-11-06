import 'package:flutter/material.dart';

import '../../shared/ui/vms_ui.dart';

/// Mess yang berlaku pada tanggal kerja jadwal: hunian APPROVED yang rentang inapnya memuat [workDate].
/// Tanggal dibandingkan sebagai tanggal kalender (tanpa jam); null bila tidak ada hunian yang cocok.
Map<String, dynamic>? messStayForDay(
  List<Map<String, dynamic>> stays,
  String workDate,
) {
  final day = DateTime.tryParse(workDate);
  if (day == null) return null;
  for (final s in stays) {
    if (s['status'] != 'APPROVED') continue;
    final start = DateTime.tryParse('${s['stay_start_date']}');
    final end = DateTime.tryParse('${s['stay_end_date']}');
    if (start == null || end == null) continue;
    if (!day.isBefore(start) && !day.isAfter(end)) return s;
  }
  return null;
}

/// Kartu "Kendaraan & alat hari ini" (ketua/anggota): aset yang dikaitkan ke jadwal ini.
class DayAssetsCard extends StatelessWidget {
  const DayAssetsCard({super.key, required this.assets});

  /// Baris dari GET /work-plans/daily/{id}/assets (LoanOut).
  final List<Map<String, dynamic>> assets;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionTitle('Kendaraan dan alat hari ini'),
        SurfaceCard(
          child: assets.isEmpty
              ? const InfoRow(
                  icon: Icons.inventory_2_outlined,
                  text: 'Tidak ada kendaraan atau alat untuk jadwal ini.',
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (var i = 0; i < assets.length; i++) ...[
                      if (i > 0) const SizedBox(height: 8),
                      InfoRow(
                        icon: assets[i]['asset_type'] == 'VEHICLE'
                            ? Icons.directions_car_outlined
                            : Icons.build_outlined,
                        text: _line(assets[i]),
                      ),
                    ],
                  ],
                ),
        ),
      ],
    );
  }

  static String _line(Map<String, dynamic> a) {
    final returned = a['returned_at'] != null;
    final holder = a['employee_name'] ?? '-';
    final state = returned ? 'sudah dikembalikan' : 'dipegang $holder';
    return '${a['asset_name']} (${a['asset_code']}) · $state';
  }
}

/// Kartu "Mess hari ini": hunian yang berlaku pada tanggal kerja jadwal.
class DayMessCard extends StatelessWidget {
  const DayMessCard({super.key, required this.stay});

  final Map<String, dynamic> stay;

  @override
  Widget build(BuildContext context) {
    final address = stay['address'] as String?;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionTitle('Mess hari ini'),
        SurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              InfoRow(
                icon: Icons.bed_outlined,
                text: '${stay['mess_name']} · ${stay['city'] ?? '-'}',
              ),
              if (address != null && address.isNotEmpty) ...[
                const SizedBox(height: 4),
                InfoRow(icon: Icons.place_outlined, text: address),
              ],
            ],
          ),
        ),
      ],
    );
  }
}
