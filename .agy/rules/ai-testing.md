---
name: Testing & Code Verification
description: Aturan pembuatan kode uji (test) oleh AI per fitur dan pemisahan pengujian lokal.
---

# Aturan Pengujian Kode (AI Testing Rules)

Sebagai AI pembangun VMS, Anda wajib menerapkan kebiasaan pengujian (testing) berikut pada setiap fitur:

1. **Uji Coba Bersamaan (TDD/Paired Testing)**:
   Setiap kali Anda menulis logika fitur (baik endpoint, service, maupun UI), Anda WAJIB membuat atau menjalankan skrip pengujian untuk memverifikasi bahwa kode tersebut benar-benar berfungsi sebelum menyatakan tugas selesai.

2. **Pemisahan Test Sementara (Lokal) vs Test Resmi (CI/CD)**:
   - **Test Sementara / Playground AI**: Skrip kotor, file percobaan manual, atau skrip pemanggilan API yang AI buat hanya untuk memastikan kodenya jalan (bukan *unit test* standar proyek) **HARUS** diletakkan di dalam folder `.local_tests/` di root proyek. 
   - Direktori `.local_tests/` telah dimasukkan ke `.gitignore`, sehingga file-file uji coba AI ini akan tetap berada di komputer lokal secara berdampingan dengan pengembangan fitur, tetapi **TIDAK AKAN PERNAH** ter-commit apalagi ter-push ke GitHub.
   
3. **Pengecualian untuk Unit Test Resmi**:
   *Unit test* resmi proyek yang terstruktur (seperti `api/tests/test_*.py` dengan pytest atau test `vitest` di web) tetap harus di-commit secara wajar karena GitHub Actions (CI/CD pipeline) sangat membutuhkannya untuk memvalidasi *Pull Request* otomatis.
