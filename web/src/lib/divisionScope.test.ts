import { describe, expect, it } from "vitest";
import { defaultBoardDivisionId } from "./divisionScope";
import type { Me } from "./types";

const pm = (division_id: string | null, managed: string[]) =>
  ({ role: "PROJECT_MANAGER", division_id, managed_division_ids: managed }) as unknown as Me;

describe("defaultBoardDivisionId", () => {
  it("PM banyak divisi: pakai divisi miliknya, bukan yang pertama", () => {
    expect(defaultBoardDivisionId(pm("b", ["a", "b"]))).toBe("b");
  });
  it("divisi milik di luar cakupan: semua divisi", () => {
    expect(defaultBoardDivisionId(pm("z", ["a", "b"]))).toBe("");
  });
  it("tanpa divisi: semua divisi", () => {
    expect(defaultBoardDivisionId(pm(null, ["a", "b"]))).toBe("");
  });
  it("OM tidak dibatasi: semua divisi", () => {
    expect(defaultBoardDivisionId({ role: "OPERATIONAL_MANAGER", division_id: "a" } as unknown as Me)).toBe("");
  });
});
