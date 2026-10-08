import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

/// Peristiwa waktu nyata dari GET /api/v1/events (SSE, T8): `topic` = notification | plan | attendance.
class LiveEvent {
  const LiveEvent(this.topic, this.data);
  final String topic;
  final Map<String, dynamic> data;
}

/// Sambungan SSE tahan putus: sambung ulang bertingkat 1 → 2 → 5 → 15 → 30 detik. Token dan refresh ditangani
/// interseptor `ApiClient` (401 → refresh → ulang). Dihentikan saat aplikasi ke latar belakang, disambung lagi
/// saat kembali. Broker server di memori satu proses; peristiwa yang terlewat saat putus dipulihkan oleh pemuatan
/// ulang layar (dan polling lonceng) — klien tidak mengandalkan peristiwa sebagai satu-satunya sumber kebenaran.
class LiveEventsClient {
  LiveEventsClient({required this.open, required this.onEvent});

  /// Membuka aliran (`VmsApi.openEvents`).
  final Future<ResponseBody> Function(CancelToken cancel) open;
  final void Function(LiveEvent event) onEvent;

  static const retry = [
    Duration(seconds: 1),
    Duration(seconds: 2),
    Duration(seconds: 5),
    Duration(seconds: 15),
    Duration(seconds: 30),
  ];

  bool _running = false;
  CancelToken? _cancel;

  bool get running => _running;

  void start() {
    if (_running) return;
    _running = true;
    unawaited(_loop());
  }

  void stop() {
    _running = false;
    _cancel?.cancel('dihentikan');
    _cancel = null;
  }

  Future<void> _loop() async {
    var attempt = 0;
    while (_running) {
      try {
        final cancel = _cancel = CancelToken();
        final body = await open(cancel);
        attempt = 0;
        var buffer = '';
        await for (final chunk in body.stream.cast<List<int>>().transform(utf8.decoder)) {
          buffer += chunk.replaceAll('\r\n', '\n');
          var cut = buffer.indexOf('\n\n');
          while (cut >= 0) {
            final event = parseBlock(buffer.substring(0, cut));
            buffer = buffer.substring(cut + 2);
            if (event != null) onEvent(event);
            cut = buffer.indexOf('\n\n');
          }
        }
      } catch (_) {
        // Putus / 401 tanpa sesi / server mati: coba lagi sesuai jeda bertingkat.
      }
      if (!_running) break;
      await Future<void>.delayed(retry[attempt < retry.length - 1 ? attempt++ : retry.length - 1]);
    }
  }

  /// Satu blok SSE → peristiwa; komentar (`: ping`) dan blok rusak → null.
  static LiveEvent? parseBlock(String block) {
    var topic = 'message';
    final data = <String>[];
    for (final line in block.split('\n')) {
      if (line.startsWith('event:')) {
        topic = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        data.add(line.substring(5).trim());
      }
    }
    if (data.isEmpty) return null;
    try {
      final decoded = jsonDecode(data.join('\n'));
      return decoded is Map ? LiveEvent(topic, Map<String, dynamic>.from(decoded)) : null;
    } catch (_) {
      return null;
    }
  }
}
