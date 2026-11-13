part of 'survey_point_screen.dart';

/// Kolom tabel "Hitungan installasi Fiber Optic (FO) CCTV" (sama dengan laporan baku, docs/37).
const foNumericColumns = [
  'Galian/Tarikan',
  'Indoor Cable',
  'Spare cable',
  'Kabel FO',
  'Kabel Power',
  'Cable Subduct',
  'Pipe 2"',
  'Patch Cord SC-SC',
  'Pigtail SC',
  'FDU',
  'Concrete Cable Cover',
  'Concrete Marker Block (Straight)',
  'Concrete Marker Block (Bend)',
  'Plastic Marker Tape',
];

/// Kebutuhan pemasangan yang sering muncul (pilih cepat; bisa ditambah sendiri).
const quickNeeds = [
  'Tangga panjang',
  'Scaffolding / Bucket Truck',
  'Grounding',
  'Galian',
  'Box Panel',
  'Izin kerja / Facility Owner',
];

class _Photo {
  _Photo({this.fileId, this.path, required this.requirementId});
  String? fileId;
  final String? path;
  final String requirementId;
}

class _Material {
  _Material(this.name, this.qty, this.unit);
  final String name;
  num qty;
  final String unit;
}
