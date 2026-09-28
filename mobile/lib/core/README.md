# core/

Infrastruktur lintas-fitur, bukan logika satu modul tertentu:

- Klien HTTP (`dio`) + interceptor auto-refresh token (401 -> panggil `/auth/refresh` -> ulangi request).
- Wrapper `flutter_secure_storage` untuk simpan/baca `access_token` & `refresh_token`.
- Konstanta (base URL API, timeout, dsb) -- base URL harus IP LAN saat testing real device, bukan `localhost`.
- Helper `client_id` (device_info_plus) untuk login.
