import 'package:flutter/material.dart';

import '../../core/theme/theme.dart';
import 'vms_ui.dart';

/// Pilihan untuk [VmsSelectField].
class VmsOption<T> {
  const VmsOption(this.value, this.label);
  final T value;
  final String label;
}

/// Kolom pilih simetris (R-14, pengganti dropdown bawaan): ikon bulat kiri, label kecil + nilai tebal
/// di tengah, chevron bulat kanan — tinggi & jarak kiri/kanan sama.
/// Ketuk → lembar bawah berisi opsi (dengan kolom pencarian instan otomatis bila opsi > 5).
class VmsSelectField<T> extends StatelessWidget {
  const VmsSelectField({
    super.key,
    required this.label,
    required this.icon,
    required this.options,
    required this.value,
    required this.onChanged,
    this.placeholder = 'Pilih',
  });
  final String label;
  final IconData icon;
  final List<VmsOption<T>> options;
  final T? value;
  final ValueChanged<T> onChanged;
  final String placeholder;

  Future<void> _open(BuildContext context) async {
    final picked = await showModalBottomSheet<T>(
      context: context,
      useSafeArea: true,
      useRootNavigator: true,
      showDragHandle: true,
      isScrollControlled: true,
      backgroundColor: VmsColors.neutral0,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (ctx) => _SelectSheet<T>(
        label: label,
        options: options,
        currentValue: value,
      ),
    );
    if (picked != null) onChanged(picked);
  }

  @override
  Widget build(BuildContext context) {
    String? current;
    for (final o in options) {
      if (o.value == value) current = o.label;
    }
    return Semantics(
      button: true,
      label: '$label: ${current ?? placeholder}',
      child: Pressable(
        onTap: options.isEmpty ? null : () => _open(context),
        child: Container(
          height: 64,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            color: VmsColors.neutral0,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: VmsColors.neutral200),
          ),
          child: Row(
            children: [
              _Circle(
                filled: true,
                child: Icon(icon, color: VmsColors.brand700, size: 21),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: VmsTextStyles.caption.copyWith(
                        color: VmsColors.neutral500,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Text(
                      current ?? placeholder,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: VmsTextStyles.body.copyWith(
                        fontWeight: FontWeight.w700,
                        color: current == null
                            ? VmsColors.neutral400
                            : VmsColors.neutral900,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              const _Circle(
                child: Icon(
                  Icons.keyboard_arrow_down_rounded,
                  color: VmsColors.brand800,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SelectSheet<T> extends StatefulWidget {
  const _SelectSheet({
    required this.label,
    required this.options,
    required this.currentValue,
  });
  final String label;
  final List<VmsOption<T>> options;
  final T? currentValue;

  @override
  State<_SelectSheet<T>> createState() => _SelectSheetState<T>();
}

class _SelectSheetState<T> extends State<_SelectSheet<T>> {
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final searchable = widget.options.length > 5;
    final needle = _q.trim().toLowerCase();
    final filtered = needle.isEmpty
        ? widget.options
        : [
            for (final o in widget.options)
              if (o.label.toLowerCase().contains(needle)) o,
          ];
    final viewInsets = MediaQuery.viewInsetsOf(context).bottom;

    return Padding(
      padding: EdgeInsets.fromLTRB(
        16,
        0,
        16,
        viewInsets > 0 ? viewInsets + 12 : safeListPadding(context).bottom,
      ),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.78,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 0, 4, 12),
              child: Text(
                widget.label,
                style: VmsTextStyles.heading.copyWith(
                  fontWeight: FontWeight.w800,
                  color: VmsColors.brand900,
                ),
              ),
            ),
            if (searchable) ...[
              TextField(
                onChanged: (v) => setState(() => _q = v),
                textInputAction: TextInputAction.search,
                decoration: InputDecoration(
                  hintText: 'Cari ${widget.label.toLowerCase()}...',
                  prefixIcon: const Icon(Icons.search_rounded),
                  isDense: true,
                  filled: true,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
              const SizedBox(height: 12),
            ],
            Flexible(
              child: filtered.isEmpty
                  ? Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        'Tidak ada pilihan yang cocok.',
                        textAlign: TextAlign.center,
                        style: VmsTextStyles.bodySm.copyWith(
                          color: VmsColors.neutral500,
                        ),
                      ),
                    )
                  : ListView(
                      shrinkWrap: true,
                      children: [
                        for (final o in filtered)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: _OptionRow(
                              label: o.label,
                              selected: o.value == widget.currentValue,
                              onTap: () => Navigator.of(context).pop(o.value),
                            ),
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

class _Circle extends StatelessWidget {
  const _Circle({required this.child, this.filled = false});
  final Widget child;
  final bool filled;
  @override
  Widget build(BuildContext context) => Container(
    width: 44,
    height: 44,
    decoration: BoxDecoration(
      shape: BoxShape.circle,
      color: filled ? VmsColors.brand50 : null,
      border: filled ? null : Border.all(color: VmsColors.neutral200),
    ),
    child: child,
  );
}

class _OptionRow extends StatelessWidget {
  const _OptionRow({
    required this.label,
    required this.selected,
    required this.onTap,
  });
  final String label;
  final bool selected;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Pressable(
    onTap: onTap,
    child: Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: selected ? VmsColors.brand50 : VmsColors.neutral0,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: selected ? VmsColors.brand300 : VmsColors.neutral200,
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: VmsTextStyles.body.copyWith(
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                color: VmsColors.neutral900,
              ),
            ),
          ),
          Icon(
            selected ? Icons.check_circle_rounded : Icons.circle_outlined,
            color: selected ? VmsColors.brand700 : VmsColors.neutral300,
            size: 22,
          ),
        ],
      ),
    ),
  );
}
