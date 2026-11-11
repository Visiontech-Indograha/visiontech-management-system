import { describe, expect, it } from "vitest";
import { canCancelLeaveRule } from "./leaveRules";

describe("canCancelLeaveRule", () => {
  const now = new Date("2026-11-11T05:00:00Z");
  const me = { role: "EMPLOYEE", employee_id: "e1" };
  it("menunggu milik sendiri dan belum lewat: boleh", () =>
    expect(canCancelLeaveRule({ status: "PENDING", employee_id: "e1", end_date: "2026-11-12" }, me, now)).toBe(true));
  it("menunggu tetapi hari terakhir sudah lewat (cuti mundur): tidak, sama dengan API", () =>
    expect(canCancelLeaveRule({ status: "PENDING", employee_id: "e1", end_date: "2026-11-10" }, me, now)).toBe(false));
  it("menunggu milik orang lain: tidak", () =>
    expect(canCancelLeaveRule({ status: "PENDING", employee_id: "e2", end_date: "2026-11-12" }, me, now)).toBe(false));
  it("disetujui: HR boleh", () =>
    expect(canCancelLeaveRule({ status: "APPROVED_BY_HR", employee_id: "e2", end_date: "2026-11-12" }, { role: "ADMIN_HR_GA", employee_id: "h" }, now)).toBe(true));
});
