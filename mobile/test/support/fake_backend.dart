import 'package:dio/dio.dart';
import 'package:drift/native.dart';
import 'package:vms_mobile/core/api_client.dart';
import 'package:vms_mobile/core/device_id.dart';
import 'package:vms_mobile/core/token_storage.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/sync_engine.dart';

/// client_id tetap tanpa menyentuh secure storage (plugin tidak ada di uji).
class FakeDeviceId implements DeviceIdProvider {
  const FakeDeviceId([this.id = 'device-uji']);
  final String id;

  @override
  Future<String> getClientId() async => id;
}

/// Penanganan satu request: kembalikan `data` (dijawab 200) atau lempar
/// [DioException] lewat [networkError] / [httpError].
typedef FakeRoute = Object? Function(RequestOptions options);

DioException networkError(RequestOptions o) => DioException(
  requestOptions: o,
  type: DioExceptionType.connectionError,
  error: 'tidak ada sinyal',
);

DioException httpError(RequestOptions o, int status, Object? data) =>
    DioException(
      requestOptions: o,
      type: DioExceptionType.badResponse,
      response: Response(requestOptions: o, statusCode: status, data: data),
    );

/// Server palsu di level Dio: interceptor bawaan [ApiClient] (yang membaca
/// token dari secure storage) dibuang, lalu setiap request dijawab dari
/// [routes] berdasarkan akhiran path. Request tanpa rute = sinyal putus.
class FakeBackend extends Interceptor {
  final Map<String, FakeRoute> routes = {};
  final List<RequestOptions> requests = [];

  /// Header respons per akhiran path (mis. `X-Next-Cursor`).
  final Map<String, Map<String, String>> responseHeaders = {};

  /// Body setiap `POST /sync/operations` yang diterima, sesuai urutan.
  List<Map<String, dynamic>> get syncBatches => [
    for (final r in requests)
      if (r.path.endsWith('/sync/operations'))
        Map<String, dynamic>.from(r.data as Map),
  ];

  /// Operasi yang terkirim, diratakan dari semua batch.
  List<Map<String, dynamic>> get sentOps => [
    for (final b in syncBatches)
      for (final op in b['operations'] as List)
        Map<String, dynamic>.from(op as Map),
  ];

  /// Jawab `/sync/operations` dengan status per operasi dari [statusFor].
  void answerSync(
    String Function(Map<String, dynamic> op) statusFor, {
    String? errorMessage,
  }) {
    routes['/sync/operations'] = (o) => {
      'results': [
        for (final op in (o.data as Map)['operations'] as List)
          {
            'client_op_id': (op as Map)['client_op_id'],
            'status': statusFor(Map<String, dynamic>.from(op)),
            'error_message': ?errorMessage,
          },
      ],
    };
  }

  void offline() => routes.clear();

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    requests.add(options);
    final route = routes.entries
        .where((e) => options.path.endsWith(e.key))
        .map((e) => e.value)
        .firstOrNull;
    if (route == null) {
      handler.reject(networkError(options));
      return;
    }
    try {
      final data = route(options);
      final h = Headers();
      responseHeaders.forEach((k, v) {
        if (options.path.endsWith(k)) {
          v.forEach(h.set);
        }
      });
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 200,
          data: data,
          headers: h,
        ),
      );
    } on DioException catch (e) {
      handler.reject(e);
    }
  }
}

AppDatabase memoryDb() => AppDatabase.forTesting(NativeDatabase.memory());

SyncEngine engineWith(AppDatabase db, FakeBackend backend) {
  final apiClient = ApiClient(tokenStorage: const TokenStorage());
  apiClient.dio.interceptors
    ..clear()
    ..add(backend);
  return SyncEngine(
    apiClient: apiClient,
    db: db,
    deviceId: const FakeDeviceId(),
  );
}
