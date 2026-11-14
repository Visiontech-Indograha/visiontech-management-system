part of 'survey_point_screen.dart';

/// Material terpilih: dari katalog (satuan baku) atau di luar katalog (satuan dari daftar).
class SurveyMaterialPick {
  const SurveyMaterialPick(this.name, this.qty, this.unit);
  final String name;
  final num qty;
  final String unit;
}

/// Satuan baku untuk material di luar katalog — tidak diketik bebas agar BoM tidak salah satuan.
const surveyUnits = ['Unit', 'Meter', 'Pasang', 'Batang', 'Roll', 'Set', 'Buah', 'Lot'];

/// Cari material di katalog atau tambah di luar katalog, lalu isi jumlah. Dipakai titik & material umum lokasi.
Future<SurveyMaterialPick?> pickSurveyMaterial(BuildContext context, List<Map> catalog) async {
  final picked = await showModalBottomSheet<Map<String, String>>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (ctx) => _MaterialPicker(catalog: catalog),
  );
  if (picked == null || !context.mounted) return null;
  final fromCatalog = picked['custom'] != '1';
  final qty = TextEditingController(text: picked['qty'] ?? '1');
  var unit = picked['unit'] ?? 'Unit';
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setLocal) => AlertDialog(
        title: Text(picked['name']!),
        content: Row(
          children: [
            Expanded(
              child: TextField(
                controller: qty,
                autofocus: true,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Jumlah'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: fromCatalog
                  ? InputDecorator(
                      decoration: const InputDecoration(labelText: 'Satuan'),
                      child: Text(unit),
                    )
                  : DropdownButtonFormField<String>(
                      initialValue: unit,
                      decoration: const InputDecoration(labelText: 'Satuan'),
                      items: [for (final u in surveyUnits) DropdownMenuItem(value: u, child: Text(u))],
                      onChanged: (v) => setLocal(() => unit = v ?? unit),
                    ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Tambah')),
        ],
      ),
    ),
  );
  final q = num.tryParse(qty.text.replaceAll(',', '.'));
  if (ok != true || q == null || q <= 0) return null;
  return SurveyMaterialPick(picked['name']!, q, unit);
}

class _MaterialPicker extends StatefulWidget {
  const _MaterialPicker({required this.catalog});
  final List<Map> catalog;

  @override
  State<_MaterialPicker> createState() => _MaterialPickerState();
}

class _MaterialPickerState extends State<_MaterialPicker> {
  final _q = TextEditingController();

  static String _qtyText(Object? v) {
    final n = num.tryParse('${v ?? 1}') ?? 1;
    return n == n.roundToDouble() ? n.toInt().toString() : n.toString();
  }

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final q = _q.text.trim().toLowerCase();
    final items = widget.catalog.where((m) => '${m['name']}'.toLowerCase().contains(q)).toList();
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SizedBox(
        height: MediaQuery.of(context).size.height * 0.7,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: TextField(
                controller: _q,
                autofocus: true,
                onChanged: (_) => setState(() {}),
                decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Cari material…'),
              ),
            ),
            if (q.isNotEmpty && !items.any((m) => '${m['name']}'.toLowerCase() == q))
              ListTile(
                leading: const Icon(Icons.add_circle_outline),
                title: Text('Tambah "${_q.text.trim()}"'),
                subtitle: const Text('Material di luar katalog'),
                onTap: () => Navigator.pop(context, {'name': _q.text.trim(), 'unit': 'Unit', 'custom': '1'}),
              ),
            Expanded(
              child: ListView(
                children: [
                  for (final m in items)
                    ListTile(
                      leading: const Icon(Icons.inventory_2_outlined),
                      title: Text('${m['name']}'),
                      subtitle: Text('${m['unit']}'),
                      onTap: () => Navigator.pop(context, {
                        'name': '${m['name']}',
                        'unit': '${m['unit']}',
                        'qty': _qtyText(m['default_qty']),
                      }),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
