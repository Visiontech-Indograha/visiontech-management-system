const ENTITIES: Record<string, string> = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&nbsp;": " " };

/**
 * Ubah HTML sederhana (isi kampanye K3) menjadi teks biasa aman:
 * tag blok (h1-h6, p, li, br, div) jadi baris/paragraf, tag lain dibuang. Hasil dirender sebagai teks (whitespace-pre-line).
 */
export function htmlToText(input: string | null | undefined): string {
  if (!input) return "";
  let s = input.replace(/<(script|style)\b[\s\S]*?<\/\1\s*>/gi, "");
  s = s.replace(/<br\s*\/?>/gi, "\n");
  s = s.replace(/<li\b[^>]*>/gi, "\n• ");
  s = s.replace(/<\/(h[1-6]|p|div|ul|ol|blockquote)\s*>/gi, "\n\n");
  s = s.replace(/<(h[1-6]|p|div|ul|ol|blockquote)\b[^>]*>/gi, "\n");
  s = s.replace(/<\/?[a-z!][^>]*>/gi, "");
  s = s.replace(/&(amp|lt|gt|quot|nbsp|#39);/g, (m) => ENTITIES[m] ?? m);
  return s
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
