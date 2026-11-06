import { describe, expect, it } from "vitest";

/** Regresi wajib dok 07 §3 yang belum punya uji: R1 (dialog bawaan). R5 (laporan harian SK) dipensiunkan di M5. */

describe("R1 · tidak ada dialog bawaan peramban", () => {
  // Seluruh kode sumber web (bukan uji) sebagai teks mentah — dikumpulkan Vite saat uji dijalankan.
  const sources = import.meta.glob(["/src/**/*.{ts,tsx}", "!/src/test/**", "!/src/**/*.test.{ts,tsx}"], {
    query: "?raw",
    import: "default",
    eager: true,
  }) as Record<string, string>;

  it("kode web tidak memanggil alert/confirm/prompt (membekukan halaman dan otomasi)", () => {
    expect(Object.keys(sources).length).toBeGreaterThan(50);
    const offenders = Object.entries(sources)
      .filter(([, text]) => /(^|[^\w.])(window\.)?(alert|confirm|prompt)\s*\(/m.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });
});
