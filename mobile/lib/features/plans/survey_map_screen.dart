import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../shared/ui/vms_ui.dart';

const _satUrl = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

/// Peta layout titik survei (citra satelit). Ketuk penanda untuk memilih titik, lalu ketuk lokasi yang tepat di
/// peta untuk memindahkannya. Posisi ini dipakai layout otomatis di laporan.
class SurveyMapScreen extends ConsumerStatefulWidget {
  const SurveyMapScreen({super.key, required this.survey});
  final Map<String, dynamic> survey;

  @override
  ConsumerState<SurveyMapScreen> createState() => _SurveyMapScreenState();
}

class _SurveyMapScreenState extends ConsumerState<SurveyMapScreen> {
  late List<Map<String, dynamic>> _points = [
    for (final p in (widget.survey['points'] as List? ?? const [])) Map<String, dynamic>.from(p as Map),
  ];
  String? _selected;
  bool _busy = false;

  bool get _canMove => widget.survey['can_move'] == true;

  LatLng? _pos(Map<String, dynamic> p) {
    final lat = double.tryParse('${p['site_lat'] ?? ''}');
    final lng = double.tryParse('${p['site_lng'] ?? ''}');
    return lat == null || lng == null ? null : LatLng(lat, lng);
  }

  void _snack(String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  Future<void> _move(LatLng to) async {
    final id = _selected;
    if (id == null || _busy) return;
    setState(() => _busy = true);
    try {
      final s = await ref.read(syncEngineProvider).api.moveSurveyPoint(id, to.latitude, to.longitude);
      if (!mounted) return;
      setState(() {
        _points = [for (final p in (s['points'] as List? ?? const [])) Map<String, dynamic>.from(p as Map)];
        _selected = null;
      });
      _snack('Posisi titik disimpan.');
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final placed = [
      for (final p in _points)
        if (_pos(p) != null) _pos(p)!,
    ];
    final selectedName = _points.where((p) => '${p['point_id']}' == _selected).map((p) => '${p['name']}').firstOrNull;
    return Scaffold(
      appBar: AppBar(title: const Text('Peta layout')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: NoticeBanner(
              icon: Icons.touch_app_rounded,
              text: !_canMove
                  ? 'Hanya lihat. Layout di laporan dibuat dari posisi titik ini.'
                  : selectedName == null
                  ? 'Ketuk penanda titik, lalu ketuk lokasi yang tepat di peta untuk memindahkannya.'
                  : 'Ketuk lokasi baru untuk "$selectedName".',
            ),
          ),
          if (_canMove && _points.any((p) => _pos(p) == null))
            SizedBox(
              height: 48,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                children: [
                  for (final p in _points.where((p) => _pos(p) == null))
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text('Taruh: ${p['name']}'),
                        selected: _selected == '${p['point_id']}',
                        onSelected: (_) => setState(() => _selected = '${p['point_id']}'),
                      ),
                    ),
                ],
              ),
            ),
          Expanded(
            child: FlutterMap(
              options: MapOptions(
                initialCenter: placed.isNotEmpty ? placed.first : const LatLng(0.79, 101.45),
                initialZoom: placed.isNotEmpty ? 18 : 12,
                maxZoom: 19,
                initialCameraFit: placed.length > 1
                    ? CameraFit.coordinates(coordinates: placed, padding: const EdgeInsets.all(60), maxZoom: 18)
                    : null,
                onTap: _canMove ? (_, at) => _move(at) : null,
              ),
              children: [
                TileLayer(urlTemplate: _satUrl, maxNativeZoom: 18, userAgentPackageName: 'com.visiontech.vms_mobile'),
                MarkerLayer(
                  markers: [
                    for (final (i, p) in _points.indexed)
                      if (_pos(p) != null)
                        Marker(
                          point: _pos(p)!,
                          width: 160,
                          height: 64,
                          alignment: Alignment.topCenter,
                          child: GestureDetector(
                            onTap: _canMove ? () => setState(() => _selected = '${p['point_id']}') : null,
                            child: _Pin(n: i + 1, name: '${p['name']}', selected: _selected == '${p['point_id']}'),
                          ),
                        ),
                  ],
                ),
                const SimpleAttributionWidget(source: Text('Esri, Maxar, Earthstar Geographics')),
              ],
            ),
          ),
          if (_busy) const LinearProgressIndicator(),
        ],
      ),
    );
  }
}

class _Pin extends StatelessWidget {
  const _Pin({required this.n, required this.name, required this.selected});
  final int n;
  final String name;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          decoration: BoxDecoration(
            color: selected ? Colors.amber : Colors.white,
            borderRadius: BorderRadius.circular(6),
            boxShadow: const [BoxShadow(blurRadius: 3, color: Colors.black38)],
          ),
          child: Text('$n. $name', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11)),
        ),
        const SizedBox(height: 2),
        Container(
          width: 28,
          height: 28,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: const Color(0xFFDC2626),
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white, width: 3),
          ),
          child: Text(
            '$n',
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12),
          ),
        ),
      ],
    );
  }
}
