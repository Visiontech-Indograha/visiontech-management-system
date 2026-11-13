import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { leaveMinStartDate, validateLeaveStart, LEAVE_BACKDATE_MESSAGE } from "./leaveRules";

describe("aturan cuti mundur", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-10T18:00:00Z")); // 11 Nov 01:00 Jakarta
  });
  afterEach(() => vi.useRealTimers());

  it("minimum = hari ini Jakarta - 3", () => {
    expect(leaveMinStartDate(["EMPLOYEE"])).toBe("2026-11-08");
  });
  it("tepat 3 hari boleh", () => {
    expect(validateLeaveStart("2026-11-08", ["EMPLOYEE"])).toBeNull();
  });
  it("hari ke-4 ditolak", () => {
    expect(validateLeaveStart("2026-11-07", ["EMPLOYEE"])).toBe(LEAVE_BACKDATE_MESSAGE);
  });
  it.each(["ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN"])("%s bebas", (r) => {
    expect(leaveMinStartDate([r])).toBeNull();
    expect(validateLeaveStart("2026-01-01", ["EMPLOYEE", r])).toBeNull();
  });
});
