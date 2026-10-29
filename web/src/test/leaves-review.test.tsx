import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { mockApi, renderRoute } from "./utils";

/** Persetujuan cuti dua tahap: PM lebih dulu, lalu HR/GA. HR harus bisa meninjau cuti yang sudah disetujui PM. */
const leave = (status: string) => ({
  leave_id: "l1", employee_id: "e1", employee_name: "Uji Ketua", employee_no: "N1", division_name: "Sipil",
  leave_type: "ANNUAL", start_date: "2026-10-29", end_date: "2026-10-30", total_days: 2, reason: "Keperluan keluarga",
  status, attachment_path: null, reviewed_by_name: null, review_note: null, create_at: "2026-10-27T10:00:00Z",
});
const handler = (status: string) => (c: { url?: string; method?: string }) => {
  if (c.url === "/leaves" && c.method === "get") return { data: [leave(status)] };
  if (c.url?.startsWith("/leaves/balance")) return { data: { total_quota: 12, used_quota: 0, remaining_quota: 12, period_year: 2026 } };
};

describe("Tinjau cuti", () => {
  it("HR melihat tombol tinjau untuk cuti yang sudah disetujui PM", async () => {
    mockApi(handler("APPROVED_BY_PM"));
    renderRoute("/leaves", { me: { ...mockMe("HR")!, role: "ADMIN_HR_GA" } });
    expect(await screen.findByRole("button", { name: "Tinjau cuti Uji Ketua" })).toBeInTheDocument();
  });

  it("PM tidak bisa meninjau lagi cuti yang sudah disetujuinya", async () => {
    mockApi(handler("APPROVED_BY_PM"));
    renderRoute("/leaves", { me: { ...mockMe("PM")!, role: "PROJECT_MANAGER" } });
    expect(await screen.findByText("Keperluan keluarga")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tinjau cuti Uji Ketua" })).not.toBeInTheDocument();
  });

  it("cuti yang masih menunggu bisa ditinjau PM", async () => {
    mockApi(handler("PENDING"));
    renderRoute("/leaves", { me: { ...mockMe("PM")!, role: "PROJECT_MANAGER" } });
    expect(await screen.findByRole("button", { name: "Tinjau cuti Uji Ketua" })).toBeInTheDocument();
  });
});
