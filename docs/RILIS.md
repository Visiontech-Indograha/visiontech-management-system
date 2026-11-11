# Rilis dan nomor build APK

Versi: `VERSION` (SemVer) -> `bash scripts/versi.sh --tulis` (menulis api, web, `mobile/pubspec.yaml` `X.Y.Z+BUILD`, BUILD = max(jumlah commit, build pubspec, lantai)); cek: `bash scripts/versi.sh`. CHANGELOG.md tidak di-commit; catatan rilis di deskripsi PR.

## Nomor build (versionCode) di `.github/workflows/apk.yml`
- Prod: BUILD = angka `+N` di `mobile/pubspec.yaml` (tidak berubah).
- Beta: BUILD = max(N pubspec, `git rev-list --count HEAD` pada cabang beta; checkout `fetch-depth: 0`). Tiap merge ke beta menambah commit, jadi build beta selalu naik dan pembaruan dalam aplikasi (`/api/v1/app/android/update?build=<n>`) mendeteksinya.
- Dipakai via `flutter build apk --build-number`, dan sama persis di `latest.json` (`build`, `min_build` bila opsi wajib).
- Jaminan: (a) naik antar build beta (commit baru); (b) tidak melebihi build prod berikutnya karena `versi.sh` memakai jumlah commit yang sama atau lebih besar; build sama (bukan lebih besar) hanya bila tidak ada commit baru; (c) jauh di bawah batas Android 2.100.000.000 (langkah workflow menolak di luar batas).
- Build ulang commit yang sama (manual) menghasilkan nomor yang sama.
- Bukti penuh hanya dari build beta berikutnya (cek `build` di `latest.json` cabang `rilis-apk-beta`).
