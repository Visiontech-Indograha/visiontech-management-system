import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

const tool = { tool_id: "t1", office_id: "o1", office_name: "Kantor Utama", division_id: null, division_name: null,
  ownership_type: "SHARED_TOOL", category: "BOR", name: "Bor Bosch", tool_code: "TL-BOR-001", status: "ready" };
const employees = { items: [{ employee_id: "e1", full_name: "Doni", employee_no: "VT-08", join_date: "2024-01-01", offboarding_status: "active" }], total: 1, page: 1, size: 25 };
const teams = [{ team_id: "tm1", name: "Tim Alfa" }, { team_id: "tm2", name: "Tim Beta" }];
const plan = { daily_plan_id: "dp1", team_id: "tm1", team_name: "Tim Alfa", division_name: "Divisi Sipil", project_title: "Proyek Utara", work_date: "2026-11-02", status: "APPROVED" };
const availability = (used: Record<string, unknown>) => [
  { asset_type: "TOOL", asset_id: "t1", asset_name: "Bor Bosch", status: "ready", available: false, used_by_team_id: "tm2", used_by_team_name: "Tim Beta", used_by_requested_team: false, ...used },
];

const openLend = async () => {
  renderRoute("/assets", { role: "ASSET" });
  fireEvent.click(await screen.findByRole("button", { name: /^Alat/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Serahkan" }));
  return screen.getByRole("dialog", { name: "Serahkan Bor Bosch" });
};

describe("Pinjam aset dengan jadwal, tim, dan ketersediaan", () => {
  it("bentrok dengan tim lain: peringatan tampil dan tombol Serahkan nonaktif", async () => {
    mockApi((c) => {
      if (c.url === "/assets/tools") return { data: [tool] };
      if (c.url === "/assets/vehicles") return { data: [] };
      if (c.url === "/assets/loans") return { data: [] };
      if (c.url === "/employees") return { data: employees };
      if (c.url === "/teams") return { data: teams };
      if (c.url === "/work-plans/daily") return { data: [] };
      if (c.url === "/assets/availability") return { data: availability({}) };
    });
    const dialog = await openLend();
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Bentrok: aset ini dipakai Tim Beta");
    expect(within(dialog).getByRole("button", { name: "Serahkan" })).toBeDisabled();
  });

  it("jadwal dipilih: ketersediaan diminta per tanggal & tim, lalu daily_plan_id ikut dikirim", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/assets/tools") return { data: [tool] };
      if (c.url === "/assets/vehicles") return { data: [] };
      if (c.url === "/assets/loans") return c.method === "post" ? { status: 201, data: {} } : { data: [] };
      if (c.url === "/employees") return { data: employees };
      if (c.url === "/teams") return { data: teams };
      if (c.url === "/work-plans/daily") return { data: [plan] };
      if (c.url === "/assets/availability") return { data: availability({ used_by_team_id: null, used_by_team_name: null, available: true }) };
    });
    const dialog = await openLend();
    await within(dialog).findByRole("option", { name: /Proyek Utara/ });
    fireEvent.change(within(dialog).getByLabelText("Jadwal harian (opsional)"), { target: { value: "dp1" } });
    expect(within(dialog).getByLabelText("Tim pemakai (opsional)")).toHaveValue("tm1");
    fireEvent.change(within(dialog).getByLabelText("Karyawan penerima"), { target: { value: "e1" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Serahkan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/assets/loans")).toBe(true));
    const avail = calls.find((c) => c.url === "/assets/availability" && (c.params as { team_id?: string } | undefined)?.team_id === "tm1");
    expect(avail?.params).toEqual({ date: expect.any(String), team_id: "tm1" });
    expect(calls.find((c) => c.method === "post" && c.url === "/assets/loans")!.data).toEqual({
      asset_type: "TOOL", tool_id: "t1", employee_id: "e1", handover_file_id: null, daily_plan_id: "dp1",
    });
  });
});
