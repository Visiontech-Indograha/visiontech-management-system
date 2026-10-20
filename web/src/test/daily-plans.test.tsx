import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

/** Jadwal harian daily-first (M5): matriks tim × hari, buat dari sel kosong, ajukan/setujui, setujui minggu. */
const todayIso = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
const options = {
  divisions: [{ division_id: "d1", name: "Sipil" }],
  teams: [
    { team_id: "t1", name: "Tim Alpha", division_id: "d1", leader_employee_id: "e-lead", leader_name: "Agus" },
    { team_id: "t2", name: "Tim Bravo", division_id: "d1", leader_employee_id: "e-x", leader_name: "Riko" },
  ],
  orders: [],
};
const plan = (over: Record<string, unknown> = {}) => ({
  daily_plan_id: "p1", division_id: "d1", division_name: "Sipil", team_id: "t1", team_name: "Tim Alpha",
  leader_employee_id: "e-lead", leader_name: "Agus", work_date: todayIso, site_name: "Gardu Induk Minas",
  site_lat: "1.4700000", site_lng: "101.4500000", attendance_radius_m: 150, clock_in_time: "07:00:00",
  clock_out_time: "16:00:00", status: "SUBMITTED", created_by_id: "e-pm", item_count: 2, done_count: 0, ...over,
});

describe("Jadwal harian", () => {
  it("PM melihat matriks minggu dan menyetujui jadwal yang menunggu", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan()] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan(), items: [], attachment_file_ids: [] } };
      if (c.url === "/work-plans/daily/p1/approve") return { data: plan({ status: "APPROVED" }) };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `Jadwal Tim Alpha ${todayIso}` }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Setujui" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/work-plans/daily/p1/approve")).toBe(true));
  });

  it("setujui minggu ini mengirim semua jadwal yang menunggu", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan(), plan({ daily_plan_id: "p2", team_id: "t2", team_name: "Tim Bravo" })] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/approve") return { data: { approved: ["p1", "p2"], skipped: [] } };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Setujui minggu ini (2)" }));
    await waitFor(() =>
      expect(calls.find((c) => c.url === "/work-plans/daily/approve")?.data).toEqual({ daily_plan_ids: ["p1", "p2"] }),
    );
  });

  it("sel kosong membuka form buat jadwal untuk tim & tanggal itu", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/daily") return { data: [] };
      if (c.url === "/work-plans/form-options") return { data: options };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `Buat jadwal Tim Bravo ${todayIso}` }));
    const dialog = await screen.findByRole("dialog", { name: "Buat jadwal harian" });
    expect(within(dialog).getByLabelText("Tim")).toHaveValue("t2");
    expect(within(dialog).getByLabelText("Tanggal")).toHaveValue(todayIso);
  });

  it("pekerja lapangan tidak melihat tombol buat/persetujuan", async () => {
    mockApi((c) => (c.url === "/work-plans/daily" ? { data: [plan({ status: "APPROVED" })] } : undefined));
    renderRoute("/work-plans", { role: "field" });
    expect(await screen.findByRole("button", { name: `Jadwal Tim Alpha ${todayIso}` })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Buat jadwal/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Setujui minggu ini/ })).toBeNull();
  });
});
