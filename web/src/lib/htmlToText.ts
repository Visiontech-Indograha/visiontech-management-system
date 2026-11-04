const BLOCK = new Set(["H1", "H2", "H3", "H4", "H5", "H6", "P", "DIV", "UL", "OL", "BLOCKQUOTE"]);
const SKIP = new Set(["SCRIPT", "STYLE"]);

function walk(node: Node, out: string[]): void {
  node.childNodes.forEach((child) => {
    if (child.nodeType === Node.TEXT_NODE) {
      out.push(child.textContent ?? "");
      return;
    }
    if (child.nodeType !== Node.ELEMENT_NODE) return;
    const el = child as Element;
    if (SKIP.has(el.tagName)) return;
    if (el.tagName === "BR") out.push("\n");
    else if (el.tagName === "LI") out.push("\n• ");
    else if (BLOCK.has(el.tagName)) out.push("\n");
    walk(el, out);
    if (BLOCK.has(el.tagName)) out.push("\n\n");
  });
}

/**
 * Ubah HTML sederhana (isi kampanye K3) menjadi teks biasa aman:
 * tag blok (h1-h6, p, li, br, div) jadi baris/paragraf, tag lain dibuang. Hasil dirender sebagai teks (whitespace-pre-line).
 * Memakai DOMParser (dokumen inert, skrip tidak dijalankan), bukan regex.
 */
export function htmlToText(input: string | null | undefined): string {
  if (!input) return "";
  const doc = new DOMParser().parseFromString(input, "text/html");
  const out: string[] = [];
  walk(doc.body, out);
  return out
    .join("")
    .split(String.fromCharCode(160)).join(" ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
