const phaseLabel = {
  'SURVEY': 'Survei',
  'PREPARATION': 'Persiapan',
  'INSTALLATION': 'Instalasi',
  'REPLACEMENT': 'Replacement',
  'MAINTENANCE': 'Maintenance',
};

String qtyText(Object? v) {
  final n = num.tryParse('$v') ?? 0;
  return n == n.roundToDouble() ? n.toStringAsFixed(0) : n.toString();
}

