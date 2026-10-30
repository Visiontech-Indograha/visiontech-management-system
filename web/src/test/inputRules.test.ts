import { describe, expect, it } from "vitest";
import { koordinatError, namaKlienError, parseTanggalInput } from "@/lib/inputRules";

describe("namaKlienError", () => {
  it("menerima nama biasa dan tanda baca umum", () => {
    expect(namaKlienError("PT Pertamina EP (Persero) & Co.")).toBeNull();
  });
  it("menolak tag HTML dan emoji dengan pesan Indonesia", () => {
    expect(namaKlienError("<script>x</script>")).toMatch(/tanda < atau >/);
    expect(namaKlienError("PT Gardu 🚀")).toMatch(/emoji/);
  });
  it("batas panjang 2..150 mengikuti API", () => {
    expect(namaKlienError("A")).toMatch(/minimal 2/);
    expect(namaKlienError("A".repeat(151))).toMatch(/maksimal 150/);
    expect(namaKlienError("A".repeat(150))).toBeNull();
  });
});

describe("koordinatError", () => {
  it("kosong boleh", () => {
    expect(koordinatError("", "")).toBeNull();
  });
  it("batas lintang -90..90 dan bujur -180..180", () => {
    expect(koordinatError("-90", "180")).toBeNull();
    expect(koordinatError("90.0000001", "0")).toMatch(/Lintang/);
    expect(koordinatError("0", "-180.5")).toMatch(/Bujur/);
    expect(koordinatError("abc", "1")).toMatch(/Lintang/);
  });
  it("harus berpasangan", () => {
    expect(koordinatError("-6.2", "")).toMatch(/berpasangan/);
  });
});

describe("parseTanggalInput", () => {
  it("menerima dd/mm/yyyy dan yyyy-mm-dd", () => {
    expect(parseTanggalInput("01/11/2026")).toBe("2026-11-01");
    expect(parseTanggalInput("1/1/2027")).toBe("2027-01-01");
    expect(parseTanggalInput("2026-11-01")).toBe("2026-11-01");
  });
  it("menolak tanggal kalender tidak nyata dan format lain", () => {
    expect(parseTanggalInput("31/02/2026")).toBeNull();
    expect(parseTanggalInput("2026/11/01")).toBeNull();
    expect(parseTanggalInput("")).toBeNull();
  });
});
