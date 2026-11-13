/**
 * Kualitas bingkai kamera untuk swafoto absen web. Fungsi murni (tanpa DOM) agar mudah diuji.
 * Petunjuk hanya saran: tidak pernah menghalangi tombol ambil foto.
 */

export interface FrameScore {
  /** Kecerahan rata-rata 0..255 (luminans). */
  brightness: number;
  /** Ketajaman (selisih piksel bertetangga); makin besar makin tajam. */
  sharpness: number;
}

export const DARK_BELOW = 70;
export const BRIGHT_ABOVE = 215;
const MIN_FACE_RATIO = 0.18;
const MAX_TILT_DEG = 20;

const luma = (d: Uint8ClampedArray, i: number) => 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];

/** Kecerahan rata-rata dan ketajaman dari data RGBA kanvas (sampel jarang agar ringan). */
export function scoreImageData(data: Uint8ClampedArray, width: number, height: number): FrameScore {
  if (width < 2 || height < 2 || data.length < width * height * 4) return { brightness: 0, sharpness: 0 };
  const step = Math.max(1, Math.floor(Math.min(width, height) / 60));
  let sum = 0;
  let diff = 0;
  let n = 0;
  for (let y = 0; y < height - 1; y += step) {
    for (let x = 0; x < width - 1; x += step) {
      const i = (y * width + x) * 4;
      const l = luma(data, i);
      sum += l;
      diff += Math.abs(l - luma(data, i + 4)) + Math.abs(l - luma(data, i + width * 4));
      n++;
    }
  }
  return n === 0 ? { brightness: 0, sharpness: 0 } : { brightness: sum / n, sharpness: diff / n };
}

/** Skor gabungan: terang yang wajar (sekitar 120) dan tajam menang. */
export function frameQuality(s: FrameScore): number {
  const exposure = 1 - Math.min(1, Math.abs(s.brightness - 125) / 125);
  return s.sharpness * (0.4 + 0.6 * exposure);
}

export function pickBestIndex(scores: FrameScore[]): number {
  let best = 0;
  scores.forEach((s, i) => {
    if (frameQuality(s) > frameQuality(scores[best])) best = i;
  });
  return best;
}

export interface FaceBox {
  width: number;
  height: number;
  /** Titik mata (bila perangkat memberikannya) untuk menghitung kemiringan. */
  eyes?: { x: number; y: number }[];
}

/** Petunjuk awam dari kecerahan; null bila sudah baik. */
export function brightnessHint(brightness: number): string | null {
  if (brightness < DARK_BELOW) return "Terlalu gelap, cari tempat lebih terang.";
  if (brightness > BRIGHT_ABOVE) return "Terlalu silau, kurangi cahaya dari belakang atau samping.";
  return null;
}

/** Petunjuk awam dari hasil FaceDetector; faces undefined = fitur tidak ada (dilewati). */
export function faceHint(faces: FaceBox[] | undefined, frameWidth: number, frameHeight: number): string | null {
  if (!faces) return null;
  if (faces.length === 0) return "Hadapkan wajah ke kamera.";
  const f = faces.reduce((a, b) => (b.width * b.height > a.width * a.height ? b : a));
  if (f.height / Math.max(1, frameHeight) < MIN_FACE_RATIO && f.width / Math.max(1, frameWidth) < MIN_FACE_RATIO) {
    return "Dekatkan wajah ke kamera.";
  }
  if (f.eyes && f.eyes.length >= 2) {
    const [a, b] = [...f.eyes].sort((p, q) => p.x - q.x);
    const tilt = Math.abs((Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI);
    if (tilt > MAX_TILT_DEG) return "Luruskan kepala, jangan terlalu miring.";
  }
  return null;
}

/** Petunjuk gabungan: kecerahan didahulukan karena paling memengaruhi pencocokan wajah. */
export function cameraHint(brightness: number, faces: FaceBox[] | undefined, w: number, h: number): string | null {
  return brightnessHint(brightness) ?? faceHint(faces, w, h);
}

/**
 * Ambil beberapa bingkai beruntun lalu pilih yang terbaik. `grab` dan `wait` disuntik (kamera/jam tiruan di tes).
 * Bingkai yang gagal diambil (null) dilewati; bila semua gagal, hasil null.
 */
export async function captureBest<T>(
  grab: () => { frame: T; score: FrameScore } | null,
  wait: (ms: number) => Promise<void>,
  count = 4,
  gapMs = 250,
): Promise<T | null> {
  const got: { frame: T; score: FrameScore }[] = [];
  for (let i = 0; i < count; i++) {
    const g = grab();
    if (g) got.push(g);
    if (i < count - 1) await wait(gapMs);
  }
  if (got.length === 0) return null;
  return got[pickBestIndex(got.map((g) => g.score))].frame;
}

/** Batas akurasi web di server (MAX_WEB_ACCURACY_M); hanya untuk teks penjelasan, server tetap memutuskan. */
export const ROUGH_ACCURACY_M = 100;

export function accuracyText(accuracyM: number | undefined): { label: string; note: string | null } | null {
  if (accuracyM === undefined || !Number.isFinite(accuracyM)) return null;
  const m = Math.round(accuracyM);
  return {
    label: `Akurasi lokasi ±${m} m`,
    note:
      m > ROUGH_ACCURACY_M
        ? "Lokasi perangkat ini kurang tepat (laptop biasanya tanpa GPS dan memakai WiFi). Absen tetap bisa dikirim; atasan dapat memeriksa bila perlu."
        : null,
  };
}
