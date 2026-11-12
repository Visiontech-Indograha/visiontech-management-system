import { describe, expect, it } from "vitest";
import { leaderCandidates, pmCandidates } from "./pmCandidates";

describe("pmCandidates", () => {
  it("menyertakan PM yang login walau peran dikosongkan API", () => {
    const items = [{ employee_id: "a", system_role: null }, { employee_id: "b", system_role: null }];
    expect(pmCandidates(items, { role: "PROJECT_MANAGER", employee_id: "b" })).toEqual([items[1]]);
  });
  it("OM melihat PM lewat system_role", () => {
    const items = [{ employee_id: "a", system_role: "PROJECT_MANAGER" }, { employee_id: "b", system_role: "EMPLOYEE" }];
    expect(pmCandidates(items, { role: "OPERATIONAL_MANAGER", employee_id: "z" })).toEqual([items[0]]);
  });
});

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
