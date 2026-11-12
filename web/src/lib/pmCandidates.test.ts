import { describe, expect, it } from "vitest";
import { leaderCandidates, pmCandidates } from "./pmCandidates";

describe("pmCandidates", () => {
  it("menyertakan PM yang login walau peran dikosongkan API", () => {
    const items = [{ employee_id: "a", system_role: null }, { employee_id: "b", system_role: null }];
    expect(pmCandidates(items, { role: "PROJECT_MANAGER", employee_id: "b" })).toEqual([items[1]]);
  });
  it("PM tetap melihat dirinya walau tak ada di daftar karyawan", () => {
    const out = pmCandidates([{ employee_id: "a", system_role: null }], { role: "PM", employee_id: "b", full_name: "Budi" });
    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({ employee_id: "b", full_name: "Budi" });
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
