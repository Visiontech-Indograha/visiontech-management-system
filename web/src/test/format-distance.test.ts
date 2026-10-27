import { describe, expect, it } from "vitest";
import { faceResultLabel, formatDistance } from "@/lib/format";

describe("formatDistance", () => {
  it("memakai meter di bawah 1 km dan km di atasnya", () => {
    expect(formatDistance(711.4)).toBe("711 m");
    expect(formatDistance(463807)).toBe("463,8 km");
    expect(formatDistance(null)).toBe("-");
  });
});

describe("faceResultLabel", () => {
  it("menerjemahkan hasil verifikasi wajah", () => {
    expect(faceResultLabel("SKIPPED")).toBe("Tidak diperiksa");
    expect(faceResultLabel("MATCH")).toBe("Cocok");
    expect(faceResultLabel("LAINNYA")).toBe("LAINNYA");
  });
});
