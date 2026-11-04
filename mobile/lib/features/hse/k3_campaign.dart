/// Kampanye K3 wajib baca (bentuk `ActiveCampaignDto` di API). Sama dengan web: `cooldown_seconds`
/// adalah durasi baca total, `media_paths` adalah id berkas foto berurutan.
class K3Campaign {
  const K3Campaign({
    required this.id,
    required this.title,
    required this.contentText,
    required this.mediaIds,
    this.mediaUrl,
    this.mediaCaptions = const [],
    required this.cooldownSeconds,
  });

  final String id;
  final String title;

  /// Isi kampanye sebagai teks biasa (HTML sudah dibuang tag-nya).
  final String contentText;

  /// Id berkas foto, berurutan. Kosong untuk kampanye lama tanpa carousel.
  final List<String> mediaIds;

  /// Gambar tunggal lama (URL) bila tidak ada `mediaIds`.
  final String? mediaUrl;

  /// Keterangan per foto, sejajar dengan `mediaIds` (kosong bila belum diisi; bisa lebih pendek).
  final List<String> mediaCaptions;

  /// Keterangan untuk foto ke-[index] (kosong bila tidak ada).
  String captionAt(int index) => index < mediaCaptions.length ? mediaCaptions[index] : '';

  /// Durasi baca wajib dalam detik.
  final int cooldownSeconds;

  factory K3Campaign.fromJson(Map<String, dynamic> json) {
    final paths = (json['media_paths'] as List?) ?? const [];
    final ids = paths.map((e) => e.toString()).toList();
    final legacy = json['media_path'] as String?;
    return K3Campaign(
      id: json['campaign_id'] as String,
      title: (json['title'] as String?) ?? 'Panduan K3',
      contentText: k3PlainText((json['content_html'] as String?) ?? ''),
      mediaIds: ids,
      mediaUrl: ids.isEmpty && legacy != null && legacy.isNotEmpty ? legacy : null,
      mediaCaptions: ((json['media_captions'] as List?) ?? const []).map((e) => e?.toString() ?? '').toList(),
      cooldownSeconds: (json['cooldown_seconds'] as num?)?.toInt() ?? 0,
    );
  }
}

/// Interval pergantian foto: durasi total dibagi jumlah foto (selaras `slideIntervalMs` di web).
int k3SlideIntervalMs(int totalSeconds, int photoCount) {
  if (photoCount <= 1) return totalSeconds * 1000;
  final ms = (totalSeconds * 1000 / photoCount).round();
  return ms < 1000 ? 1000 : ms;
}

/// Sisa detik wajib baca (dibulatkan ke atas, tidak pernah negatif).
int k3RemainingSeconds(int totalSeconds, int elapsedMs) {
  final left = (totalSeconds * 1000 - elapsedMs) / 1000;
  return left <= 0 ? 0 : left.ceil();
}

/// Ubah HTML kampanye menjadi teks biasa yang mudah dibaca di HP.
String k3PlainText(String html) {
  var s = html
      .replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '\n')
      .replaceAll(RegExp(r'</(p|div|li|h[1-6])>', caseSensitive: false), '\n');
  s = s.replaceAll(RegExp(r'<[^>]*>'), '');
  s = s
      .replaceAll('&nbsp;', ' ')
      .replaceAll('&quot;', '"')
      .replaceAll('&#39;', "'")
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>')
      .replaceAll('&amp;', '&');
  return s.replaceAll(RegExp(r'\n{3,}'), '\n\n').trim();
}
