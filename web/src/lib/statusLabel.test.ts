import { describe, expect, it } from "vitest";
import { statusLabel } from "./labels";
import { phaseLabel } from "./workPhase";

describe("label status dan fase", () => {
  it("status perintah kerja memakai bahasa awam", () => {
    expect(statusLabel("SURVEY_IN_PROGRESS")).toBe("Survei berjalan");
    expect(statusLabel("SURVEY_SUBMITTED")).toBe("Survei terkirim");
    expect(statusLabel("WAITING_SURVEY")).toBe("Menunggu survei");
    expect(statusLabel("READY_TO_EXECUTE")).toBe("Siap dikerjakan");
  });
  it("fase memakai istilah Indonesia", () => {
    expect(phaseLabel("REPLACEMENT")).toBe("Penggantian");
    expect(phaseLabel("MAINTENANCE")).toBe("Pemeliharaan");
  });
});
