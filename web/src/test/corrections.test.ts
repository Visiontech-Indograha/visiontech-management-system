import { describe, expect, it } from "vitest";
import { CORRECTION_STATUS, correctionActions } from "@/services/dailyPlanService";

describe("keputusan koreksi laporan harian", () => {
  it("permintaan baru: setujui atau tolak (tolak wajib catatan)", () => {
    expect(correctionActions("REQUESTED")).toEqual([
      { decision: "APPROVE", label: "Setujui revisi", needsNote: false },
      { decision: "REJECT", label: "Tolak", needsNote: true },
    ]);
  });

  it("revisi masuk: terima atau kembalikan (kembalikan wajib catatan)", () => {
    expect(correctionActions("IN_REVIEW").map((a) => [a.decision, a.needsNote])).toEqual([
      ["ACCEPT", false],
      ["RETURN", true],
    ]);
  });

  it("status lain tidak punya aksi untuk PM", () => {
    for (const status of ["REVISING", "ACCEPTED", "REJECTED"] as const) {
      expect(correctionActions(status)).toEqual([]);
    }
  });

  it("setiap status punya label", () => {
    expect(Object.keys(CORRECTION_STATUS).sort()).toEqual(["ACCEPTED", "IN_REVIEW", "REJECTED", "REQUESTED", "REVISING"]);
  });
});
