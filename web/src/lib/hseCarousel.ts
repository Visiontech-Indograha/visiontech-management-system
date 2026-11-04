/**
 * Logika murni carousel kampanye K3 (tanpa React): interval auto-geser, sisa waktu wajib baca, dan
 * pergantian indeks. Aturan selaras dengan API (api/app/modules/hse/services/hse_service.py).
 */

/** Batas durasi baca untuk kampanye bergambar (detik). */
export const CAROUSEL_MIN_SECONDS = 10;
export const CAROUSEL_MAX_SECONDS = 300;
/** Minimal waktu tampil per foto (detik). */
export const CAROUSEL_SECONDS_PER_PHOTO = 3;
/** Batas jumlah foto per kampanye. */
export const CAROUSEL_MAX_PHOTOS = 8;

/** Interval pergantian foto: durasi total dibagi jumlah foto (50 dtk / 5 foto = 10 dtk). */
export function slideIntervalMs(totalSeconds: number, photoCount: number): number {
  if (photoCount <= 1) return Math.max(0, totalSeconds) * 1000;
  return Math.max(1000, Math.round((totalSeconds * 1000) / photoCount));
}

/** Sisa detik wajib baca dari waktu yang sudah berlalu (dibulatkan ke atas, tidak pernah negatif). */
export function remainingSeconds(totalSeconds: number, elapsedMs: number): number {
  return Math.max(0, Math.ceil((totalSeconds * 1000 - elapsedMs) / 1000));
}

/** Persentase kemajuan waktu wajib baca, 0-100. */
export function readProgressPercent(totalSeconds: number, elapsedMs: number): number {
  if (totalSeconds <= 0) return 100;
  return Math.min(100, Math.max(0, (elapsedMs / (totalSeconds * 1000)) * 100));
}

/** Indeks foto berikutnya, berputar ke awal di akhir daftar. */
export function nextSlideIndex(index: number, count: number): number {
  if (count <= 0) return 0;
  return (index + 1) % count;
}

/** Indeks foto sebelumnya, berputar ke akhir daftar di awal daftar. */
export function prevSlideIndex(index: number, count: number): number {
  if (count <= 0) return 0;
  return (index - 1 + count) % count;
}

/** Pesan galat bila konfigurasi kampanye bergambar melanggar aturan; null bila valid. */
export function carouselConfigError(photoCount: number, totalSeconds: number): string | null {
  if (photoCount > CAROUSEL_MAX_PHOTOS) return `Maksimal ${CAROUSEL_MAX_PHOTOS} foto per kampanye.`;
  if (photoCount === 0) return null;
  if (totalSeconds < CAROUSEL_MIN_SECONDS || totalSeconds > CAROUSEL_MAX_SECONDS) {
    return `Durasi baca harus ${CAROUSEL_MIN_SECONDS} sampai ${CAROUSEL_MAX_SECONDS} detik.`;
  }
  if (totalSeconds < photoCount * CAROUSEL_SECONDS_PER_PHOTO) {
    return `Durasi baca minimal ${CAROUSEL_SECONDS_PER_PHOTO} detik per foto (${photoCount} foto, minimal ${
      photoCount * CAROUSEL_SECONDS_PER_PHOTO
    } detik).`;
  }
  return null;
}
