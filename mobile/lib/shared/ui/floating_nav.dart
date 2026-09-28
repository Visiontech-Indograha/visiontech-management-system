import 'package:flutter/material.dart';

import '../../core/theme/theme.dart';

class FloatingNavItem {
  const FloatingNavItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
  });
  final IconData icon;
  final IconData activeIcon;
  final String label;
}

/// Navigasi bawah datar ala rujukan Dribbble (R-14): menyatu dengan latar halaman, garis tipis di
/// atas, semua tab berlabel; tab aktif = ikon terisi + label navy tebal + titik emas kecil.
class FloatingNavBar extends StatelessWidget {
  const FloatingNavBar({
    super.key,
    required this.items,
    required this.currentIndex,
    required this.onTap,
  });
  final List<FloatingNavItem> items;
  final int currentIndex;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final dur = (MediaQuery.maybeDisableAnimationsOf(context) ?? false)
        ? Duration.zero
        : const Duration(milliseconds: 240);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        border: const Border(top: BorderSide(color: VmsColors.neutral200)),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 66,
          child: Row(
            children: [
              for (final (i, item) in items.indexed)
                Expanded(
                  child: _NavTab(
                    item: item,
                    active: i == currentIndex,
                    duration: dur,
                    onTap: () => onTap(i),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavTab extends StatelessWidget {
  const _NavTab({
    required this.item,
    required this.active,
    required this.duration,
    required this.onTap,
  });
  final FloatingNavItem item;
  final bool active;
  final Duration duration;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fg = active ? VmsColors.brand700 : VmsColors.neutral500;
    return Semantics(
      button: true,
      selected: active,
      label: item.label,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedScale(
              duration: duration,
              curve: Curves.easeOutBack,
              scale: active ? 1.08 : 1,
              child: Icon(
                active ? item.activeIcon : item.icon,
                color: fg,
                size: 24,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                AnimatedContainer(
                  duration: duration,
                  width: active ? 5 : 0,
                  height: 5,
                  margin: EdgeInsets.only(right: active ? 4 : 0),
                  decoration: const BoxDecoration(
                    color: VmsColors.gold,
                    shape: BoxShape.circle,
                  ),
                ),
                Flexible(
                  child: Text(
                    item.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: VmsTextStyles.caption.copyWith(
                      color: active ? VmsColors.brand800 : VmsColors.neutral500,
                      fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                      fontSize: 11.5,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
