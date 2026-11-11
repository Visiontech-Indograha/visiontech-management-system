import { describe, expect, it } from "vitest";
import { defaultPhaseOptions, defaultsLabel, slotSummary } from "@/lib/jenisPekerjaan";

describe("pratinjau slot foto", () => {
  it("tanpa slot", () => {
    expect(slotSummary([])).toBe("Tanpa template foto");
  });

  it("menghitung jumlah, wajib, dan contoh", () => {
    expect(
      slotSummary([
        { required: true, example_file_id: "a" },
        { required: false, example_file_id: null },
        { required: true, example_file_id: null },
      ]),
    ).toBe("3 slot · 2 wajib · 1 dengan contoh");
  });
});

describe("fase bawaan per peran", () => {
  it("survei hanya untuk jenis survei", () => {
    expect(defaultPhaseOptions("SURVEY_TASK")).toContain("SURVEY");
    expect(defaultPhaseOptions("SURVEY_POINT")).toContain("SURVEY");
    expect(defaultPhaseOptions("INSTALLATION")).not.toContain("SURVEY");
    expect(defaultPhaseOptions("WORK")).not.toContain("SURVEY");
  });

  it("pilihan tetap lengkap untuk jenis biasa", () => {
    expect(defaultPhaseOptions("MAINTENANCE")).toEqual(["PREPARATION", "INSTALLATION", "REPLACEMENT", "MAINTENANCE"]);
  });
});

describe("label satuan dan fase", () => {
  it("fase kosong berarti mengikuti peran", () => {
    expect(defaultsLabel("Meter", null)).toBe("Satuan: Meter · Fase bawaan: mengikuti peran");
  });

  it("fase tersimpan memakai label lapangan", () => {
    expect(defaultsLabel("", "REPLACEMENT")).toBe("Satuan: Unit · Fase bawaan: Penggantian");
  });
});
