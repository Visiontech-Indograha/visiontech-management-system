import { describe, expect, it } from "vitest";
import { STATUS_BANDING, STATUS_LABEL, selisihLabel } from "./hikvisionBanding";

describe("hikvisionBanding", () => {
  it("setiap status punya label awam", () => {
    expect(STATUS_BANDING.map((s) => STATUS_LABEL[s])).toEqual(["Cocok", "Waktu berbeda", "Hanya di mesin", "Hanya di aplikasi"]);
  });
  it("selisih memakai kalimat awam", () => {
    expect(selisihLabel(null)).toBe("-");
    expect(selisihLabel(0)).toBe("Sama");
    expect(selisihLabel(7)).toBe("7 menit lebih lambat di mesin");
    expect(selisihLabel(-3)).toBe("3 menit lebih awal di mesin");
  });
});
