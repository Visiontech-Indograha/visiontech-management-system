/**
 * web/src/lib/mediaUtils.ts
 * Utilitas resolusi URL media dan kompresi foto sisi klien (client-side image compression).
 */

/**
 * Mengubah path storage relatif menjadi URL preview stream inline di browser.
 * Menghindari bug broken image pada berkas storage backend.
 */
export function toPreviewUrl(path: string | null | undefined): string {
  if (!path) return "/placeholder-image.png";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (path.startsWith("blob:") || path.startsWith("data:")) return path;
  if (path.startsWith("/api/")) return path;

  return `/api/v1/media/preview?path=${encodeURIComponent(path)}`;
}

/**
 * Mengubah path storage relatif menjadi URL download berkas (attachment).
 */
export function toDownloadUrl(path: string | null | undefined): string {
  if (!path) return "#";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (path.startsWith("/api/")) return path;
  return `/api/v1/media/download?path=${encodeURIComponent(path)}`;
}

/**
 * Deteksi kategori berkas berdasarkan ekstensi nama file, path, atau parameter format.
 */
export type FileCategory = "image" | "pdf" | "word" | "excel" | "powerpoint" | "unknown";

export function detectFileCategory(path: string | null | undefined): FileCategory {
  if (!path) return "unknown";
  const lower = path.toLowerCase();
  if (lower.includes("format=pdf") || lower.endsWith("/pdf") || lower.endsWith(".pdf")) {
    return "pdf";
  }
  if (lower.includes("format=docx") || lower.endsWith(".doc") || lower.endsWith(".docx")) {
    return "word";
  }
  if (lower.includes("format=xlsx") || lower.endsWith(".xls") || lower.endsWith(".xlsx")) {
    return "excel";
  }
  if (lower.includes("format=pptx") || lower.endsWith(".ppt") || lower.endsWith(".pptx")) {
    return "powerpoint";
  }
  const clean = lower.split("?")[0];
  if (clean.endsWith(".jpg") || clean.endsWith(".jpeg") || clean.endsWith(".png") || clean.endsWith(".webp") || clean.endsWith(".svg")) {
    return "image";
  }
  return "unknown";
}

/**
 * Kompresi gambar sisi klien sebelum diunggah ke backend.
 * Mempercepat proses unggah foto absensi dan laporan lapangan pada jaringan seluler.
 */
export async function compressImageClient(
  file: File,
  maxWidth = 1600,
  quality = 0.82
): Promise<File> {
  // Hanya kompresi tipe JPEG, PNG, dan WebP
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
    return file;
  }

  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target?.result as string;
      img.onload = () => {
        let width = img.width;
        let height = img.height;

        if (width > maxWidth) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        }

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext("2d");
        if (!ctx) {
          resolve(file);
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              resolve(file);
              return;
            }
            const compressed = new File([blob], file.name, {
              type: "image/jpeg",
              lastModified: Date.now(),
            });
            // Gunakan hasil kompresi hanya jika ukurannya lebih kecil dari aslinya
            resolve(compressed.size < file.size ? compressed : file);
          },
          "image/jpeg",
          quality
        );
      };
      img.onerror = () => resolve(file);
    };
    reader.onerror = () => resolve(file);
  });
}
