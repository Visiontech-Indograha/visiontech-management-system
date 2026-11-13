import { describe, expect, it } from "vitest";
import { answerLabel, inspectionStatusLabel, inspectionStatusTone, periodLabel } from "./inspectionLabels";

describe("inspectionLabels", () => {
  it("memakai kata awam", () => {
    expect(periodLabel("WEEKLY")).toBe("Mingguan");
    expect(inspectionStatusLabel("REJECTED")).toBe("Ditolak HSE");
    expect(answerLabel("PERLU_PERBAIKAN")).toBe("Perlu perbaikan");
    expect(answerLabel(undefined)).toBe("-");
  });
  it("warna status", () => {
    expect(inspectionStatusTone("VERIFIED")).toBe("success");
    expect(inspectionStatusTone("SUBMITTED")).toBe("warning");
  });
});
