/** Pemeriksaan kualitas foto K3 di sisi klien (hanya peringatan, tidak memblokir unggah). */

export const MIN_SHORT_SIDE_PX = 1000;
export const RECOMMENDED_LONG_SIDE_PX = 1600;

export interface PhotoSize {
  width: number;
  height: number;
}

export type Orientation = "portrait" | "landscape" | "square";

export function orientationOf({ width, height }: PhotoSize): Orientation {
  if (width === height) return "square";
  return width > height ? "landscape" : "portrait";
}

export const LOW_RES_MESSAGE =
  "Resolusi rendah, teks kecil mungkin sulit dibaca di HP; " +
  `disarankan minimal ${RECOMMENDED_LONG_SIDE_PX}px sisi panjang.`;

/** Peringatan resolusi rendah bila sisi terpendek < 1000 px; null bila cukup. */
export function lowResolutionWarning(size: PhotoSize): string | null {
  return Math.min(size.width, size.height) >= MIN_SHORT_SIDE_PX ? null : LOW_RES_MESSAGE;
}

/** Ringkasan bila foto dalam satu kampanye campur potret dan lanskap; null bila seragam. */
export function mixedOrientationNote(sizes: PhotoSize[]): string | null {
  const kinds = new Set(sizes.map((s) => orientationOf(s)).filter((k) => k !== "square"));
  if (kinds.size < 2) return null;
  return "Campuran potret dan lanskap: sebagian foto akan tampil lebih kecil di HP. Disarankan orientasi seragam.";
}

/** Membaca ukuran piksel asli sebuah berkas gambar di peramban. */
export function readImageSize(file: File): Promise<PhotoSize> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight });
      URL.revokeObjectURL(url);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("gambar tidak terbaca"));
    };
    img.src = url;
  });
}
