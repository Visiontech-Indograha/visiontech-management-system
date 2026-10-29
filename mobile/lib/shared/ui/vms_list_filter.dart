import 'dart:async';

import 'package:flutter/material.dart';

/// Opsi filter (chip) di bawah kolom cari. `value` kosong = semua.
class VmsFilterOption {
  const VmsFilterOption(this.value, this.label);
  final String value;
  final String label;
}

/// Keadaan cari + chip + "muat lebih banyak" untuk daftar yang sudah dimuat penuh (dan ter-cache, jadi jalan offline).
class ListQuery extends ChangeNotifier {
  ListQuery({this.pageSize = 20}) : shown = pageSize;

  final int pageSize;
  String q = '';
  String chip = '';
  int shown;

  bool get active => q.isNotEmpty || chip.isNotEmpty;

  void setQuery(String value) {
    final v = value.trim();
    if (v == q) return;
    q = v;
    shown = pageSize;
    notifyListeners();
  }

  void setChip(String value) {
    if (value == chip) return;
    chip = value;
    shown = pageSize;
    notifyListeners();
  }

  void reset() {
    q = '';
    chip = '';
    shown = pageSize;
    notifyListeners();
  }

  void loadMore() {
    shown += pageSize;
    notifyListeners();
  }

  /// Saring (kata kunci tanpa beda huruf + chip) lalu kembalikan semua hasil; potong dengan [visible].
  List<T> filter<T>(
    Iterable<T> items,
    Iterable<Object?> Function(T item) haystack, {
    bool Function(T item, String chip)? chipTest,
  }) {
    final needle = q.toLowerCase();
    return [
      for (final it in items)
        if ((chip.isEmpty || chipTest == null || chipTest(it, chip)) &&
            (needle.isEmpty || haystack(it).any((v) => (v ?? '').toString().toLowerCase().contains(needle))))
          it,
    ];
  }

  List<T> visible<T>(List<T> filtered) => filtered.length <= shown ? filtered : filtered.sublist(0, shown);
}

/// Kolom cari (debounce 250 ms, maks 100 huruf) + baris chip filter.
class VmsSearchBar extends StatefulWidget {
  const VmsSearchBar({super.key, required this.query, required this.hint, this.chips = const []});

  final ListQuery query;
  final String hint;
  final List<VmsFilterOption> chips;

  @override
  State<VmsSearchBar> createState() => _VmsSearchBarState();
}

class _VmsSearchBarState extends State<VmsSearchBar> {
  final _ctrl = TextEditingController();
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _ctrl.text = widget.query.q;
    widget.query.addListener(_sync);
  }

  /// Reset dari luar (mis. tombol "Atur ulang") mengosongkan kolom.
  void _sync() {
    if (widget.query.q.isEmpty && _ctrl.text.isNotEmpty) _ctrl.clear();
  }

  @override
  void dispose() {
    widget.query.removeListener(_sync);
    _debounce?.cancel();
    _ctrl.dispose();
    super.dispose();
  }

  void _onChanged(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 250), () => widget.query.setQuery(v));
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.query,
      builder: (context, _) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _ctrl,
              maxLength: 100,
              textInputAction: TextInputAction.search,
              onChanged: _onChanged,
              decoration: InputDecoration(
                counterText: '',
                hintText: widget.hint,
                prefixIcon: const Icon(Icons.search_rounded),
                suffixIcon: _ctrl.text.isEmpty
                    ? null
                    : IconButton(
                        tooltip: 'Hapus pencarian',
                        icon: const Icon(Icons.close_rounded),
                        onPressed: () {
                          _ctrl.clear();
                          widget.query.setQuery('');
                          setState(() {});
                        },
                      ),
                isDense: true,
                filled: true,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
              ),
            ),
            if (widget.chips.isNotEmpty) ...[
              const SizedBox(height: 8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    for (final c in widget.chips)
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: Text(c.label),
                          selected: widget.query.chip == c.value,
                          onSelected: (_) => widget.query.setChip(c.value),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Tombol "Muat lebih banyak" + keterangan jumlah; kosong bila semua sudah tampil.
class VmsLoadMore extends StatelessWidget {
  const VmsLoadMore({super.key, required this.query, required this.total, this.noun = 'data'});

  final ListQuery query;
  final int total;
  final String noun;

  @override
  Widget build(BuildContext context) {
    final shown = total < query.shown ? total : query.shown;
    if (total == 0) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Column(
        children: [
          Text('Menampilkan $shown dari $total $noun', style: Theme.of(context).textTheme.bodySmall),
          if (total > query.shown) TextButton(onPressed: query.loadMore, child: const Text('Muat lebih banyak')),
        ],
      ),
    );
  }
}

/// Keadaan kosong bila pencarian/filter tidak menemukan apa pun, dengan tombol atur ulang.
class VmsNoMatch extends StatelessWidget {
  const VmsNoMatch({super.key, required this.query});

  final ListQuery query;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(24),
    child: Column(
      children: [
        const Text('Tidak ada yang cocok dengan pencarian atau filter.', textAlign: TextAlign.center),
        TextButton(onPressed: query.reset, child: const Text('Atur ulang')),
      ],
    ),
  );
}
