import { describe, expect, it } from "vitest";
import { leaderCandidates } from "./pmCandidates";

describe("leaderCandidates", () => {
  it("hanya TEAM_LEADER bila peran terlihat", () => {
    const items = [{ system_role: "TEAM_LEADER" }, { system_role: "EMPLOYEE" }];
    expect(leaderCandidates(items)).toEqual([items[0]]);
  });
  it("tak menyaring bila peran dikosongkan API", () => {
    const items = [{ system_role: null }, { system_role: null }];
    expect(leaderCandidates(items)).toHaveLength(2);
  });
});
