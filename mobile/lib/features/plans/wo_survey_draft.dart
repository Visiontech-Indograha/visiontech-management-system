/// Isi survei work order di HP dan aturan kirimnya (sama dengan `SurveySubmitIn` di API).
const woSurveyPointNameMax = 150; // SurveyPointIn.point_name max_length
const woSurveyNarrativeMax = 2000;
const woSurveyRemarksMax = 1000;
const woSurveyBomNameMax = 150;
const woSurveyFormats = ['CCTV', 'ACS'];

class WoBomLine {
  WoBomLine({this.name = '', this.qty = 1, this.unit = 'unit'});
  String name;
  num qty;
  String unit;

  Map<String, dynamic> toJson() => {'name': name.trim(), 'qty': qty, 'unit': unit.trim()};
}

class WoSurveyPoint {
  WoSurveyPoint({
    this.name = '',
    this.workTypeId,
    this.lat,
    this.lng,
    this.remarks = '',
    List<String>? photoPaths,
    List<WoBomLine>? bom,
  }) : photoPaths = photoPaths ?? [],
       bom = bom ?? [];

  String name;
  String? workTypeId;
  double? lat;
  double? lng;
  String remarks;
  final List<String> photoPaths;
  final List<WoBomLine> bom;
}

class WoSurveyDraft {
  WoSurveyDraft({this.narrative = '', this.format = 'CCTV', List<WoSurveyPoint>? points})
    : points = points ?? [];

  String narrative;
  String format;
  final List<WoSurveyPoint> points;

  /// Pesan galat awam, atau null bila boleh dikirim.
  String? validate() {
    if (points.isEmpty) return 'Tambah minimal satu titik survei.';
    if (narrative.trim().length > woSurveyNarrativeMax) {
      return 'Catatan survei terlalu panjang (paling banyak $woSurveyNarrativeMax huruf).';
    }
    for (var i = 0; i < points.length; i++) {
      final p = points[i];
      final n = 'Titik ${i + 1}';
      final name = p.name.trim();
      if (name.isEmpty) return '$n: isi nama titik.';
      if (name.length > woSurveyPointNameMax) {
        return '$n: nama titik terlalu panjang (paling banyak $woSurveyPointNameMax huruf).';
      }
      if (p.workTypeId == null || p.workTypeId!.isEmpty) return '$n: pilih jenis pekerjaan.';
      if (p.remarks.trim().length > woSurveyRemarksMax) {
        return '$n: catatan terlalu panjang (paling banyak $woSurveyRemarksMax huruf).';
      }
      for (final b in p.bom) {
        if (b.name.trim().isEmpty || b.name.trim().length > woSurveyBomNameMax) {
          return '$n: nama barang kebutuhan harus diisi (paling banyak $woSurveyBomNameMax huruf).';
        }
        if (b.qty <= 0) return '$n: jumlah barang harus lebih dari nol.';
      }
    }
    return null;
  }

  /// Muatan op `WO_SURVEY_SUBMIT`. Foto titik ikut sebagai `local_files` (diunggah antrean sebelum kirim).
  Map<String, dynamic> toPayload(String workOrderId) => {
    'work_order_id': workOrderId,
    'survey': {
      'narrative': narrative.trim(),
      'format': format,
      'points': [
        for (final p in points)
          {
            'point_name': p.name.trim(),
            'recommended_work_type_id': p.workTypeId,
            'site_lat': ?p.lat,
            'site_lng': ?p.lng,
            'recommended_bom': [for (final b in p.bom) b.toJson()],
            'remarks': p.remarks.trim(),
            'photos': <Map<String, dynamic>>[],
            if (p.photoPaths.isNotEmpty) 'local_files': List<String>.from(p.photoPaths),
          },
      ],
      'general_bom': <Map<String, dynamic>>[],
    },
  };
}
