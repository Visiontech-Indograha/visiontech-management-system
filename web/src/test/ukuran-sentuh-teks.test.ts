import { describe, expect, it } from "vitest";

const berkas = import.meta.glob(["../**/*.{ts,tsx}", "!../**/*.test.{ts,tsx}"], {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

// Pengecualian eksplisit: kosong. Tambah hanya dengan alasan tertulis.
const KECUALI_TEKS: string[] = [];

describe("ukuran teks dan target sentuh", () => {
  it("tidak ada teks di bawah 12px (text-[10px] / text-[11px])", () => {
    const pelanggar = Object.entries(berkas)
      .filter(([f]) => !KECUALI_TEKS.some((k) => f.endsWith(k)))
      .filter(([, isi]) => /text-\[1[01]px\]/.test(isi))
      .map(([f]) => f);
    expect(pelanggar).toEqual([]);
  });

  it("Button tidak mengecil ke 36px dan tiap ukuran minimal 44px", () => {
    const src = berkas["../components/atoms/Button.tsx"];
    expect(src).toBeTruthy();
    expect(src).not.toMatch(/lg:(h|size)-(8|9)\b/);
    const blok = src.slice(src.indexOf("size: {"), src.indexOf("defaultVariants"));
    expect(blok).not.toMatch(/\b(h|size)-(8|9|10)\b/);
  });
});
