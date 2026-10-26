import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/timezone.dart' as tz;

/// Notifikasi sistem Android tanpa FCM (T8): ditampilkan saat peristiwa SSE `notification` masuk selama aplikasi
/// hidup. Notifikasi saat aplikasi ditutup penuh butuh FCM (di luar target Sabtu; lihat CHANGELOG).
class LocalNotifier {
  LocalNotifier({FlutterLocalNotificationsPlugin? plugin})
    : _plugin = plugin ?? FlutterLocalNotificationsPlugin();

  final FlutterLocalNotificationsPlugin _plugin;
  bool _ready = false;
  int _nextId = 1;

  /// Dipanggil saat notifikasi diketuk: `payload` = `plan_id|kind` (kosong bila tak ada rencana kerja).
  void Function(String payload)? onTap;

  Future<void> init() async {
    if (_ready || kIsWeb || !Platform.isAndroid) return;
    await _plugin.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      ),
      onDidReceiveNotificationResponse: (r) {
        final payload = r.payload;
        if (payload != null && payload.isNotEmpty) onTap?.call(payload);
      },
    );
    _ready = true;
  }

  /// Android 13+: izin notifikasi diminta saat runtime. Aman dipanggil berulang.
  Future<void> requestPermission() async {
    if (!_ready) await init();
    await _plugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.requestNotificationsPermission();
  }

  /// Alarm sistem pada [when]; tetap bunyi walau aplikasi ditutup. Android saja.
  Future<void> scheduleAt(int id, tz.TZDateTime when, String title, String body) async {
    if (!_ready) await init();
    if (!_ready) return;
    await _plugin.zonedSchedule(
      id: id,
      title: title,
      body: body,
      scheduledDate: when,
      notificationDetails: const NotificationDetails(
        android: AndroidNotificationDetails(
          'vms_reminder',
          'Pengingat absen',
          channelDescription: 'Pengingat absen masuk dan pulang',
          importance: Importance.high,
          priority: Priority.high,
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
    );
  }

  Future<void> cancelIds(Iterable<int> ids) async {
    if (!_ready) await init();
    if (!_ready) return;
    for (final id in ids) {
      await _plugin.cancel(id: id);
    }
  }

  Future<void> show({
    required String title,
    required String body,
    String payload = '',
  }) async {
    if (!_ready) await init();
    if (!_ready) return;
    await _plugin.show(
      id: _nextId++,
      title: title,
      body: body,
      notificationDetails: const NotificationDetails(
        android: AndroidNotificationDetails(
          'vms_live',
          'Pemberitahuan kerja',
          channelDescription: 'Perubahan rencana kerja, revisi, dan absensi',
          importance: Importance.high,
          priority: Priority.high,
          styleInformation: BigTextStyleInformation(''),
        ),
      ),
      payload: payload,
    );
  }
}
