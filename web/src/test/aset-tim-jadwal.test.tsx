import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

/** Dialog jadwal harian: aset bawaan tim (team_id) dan ketersediaannya pada tanggal jadwal. */
const todayIso = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
const dayLabel = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" })
  .format(new Date(`${todayIso}T00:00:00Z`));
const options = {
  divisions: [{ division_id: "d1", name: "Sipil" }],
  teams: [
    { team_id: "t1", name: "Tim Alpha", division_id: "d1", leader_employee_id: "e-lead", leader_name: "Agus" },
    { team_id: "t2", name: "Tim Bravo", division_id: "d1", leader_employee_id: "e-x", leader_name: "Riko" },
  ],
  orders: [],
};
const tool = (over: Record<string, unknown>) => ({
  tool_id: "tl1", office_id: "o1", office_name: "Kantor Utama", division_id: "d1", division_name: "Sipil",
  ownership_type: "SHARED_TOOL", category: "BOR", name: "Bor Bosch", tool_code: "TL-1", status: "ready",
  team_id: "t2", team_name: "Tim Bravo", ...over,
});
const vehicle = (over: Record<string, unknown>) => ({
  vehicle_id: "v1", office_id: "o1", office_name: "Kantor Utama", division_id: "d1", division_name: "Sipil",
  name: "Truk Hino", plate_no: "BK 1 AA", status: "ready", team_id: "t2", team_name: "Tim Bravo", ...over,
});

/** Buka dialog "Buat jadwal harian" untuk Tim Bravo pada hari ini. */
async function openCreateForBravo(handlers: Parameters<typeof mockApi>[0]) {
  mockApi((c) => {
    if (c.url === "/work-plans/daily") return { data: [] };
    if (c.url === "/work-plans/form-options") return { data: options };
    return handlers(c);
  });
  renderRoute("/work-plans", { role: "PM" });
  fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: kosong` }));
  fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Tim Bravo/ }));
  return screen.findByRole("dialog", { name: "Buat jadwal harian" });
}

describe("Aset tim pada jadwal harian", () => {
  it("aset bawaan tim yang dipakai tim lain pada tanggal itu menampilkan bentrok dengan nama tim pemakai", async () => {
    const dialog = await openCreateForBravo((c) => {
      if (c.url === "/assets/tools") return { data: [tool({})] };
      if (c.url === "/assets/vehicles") return { data: [] };
      if (c.url === "/assets/availability") return {
        data: [{ asset_type: "TOOL", asset_id: "tl1", asset_name: "Bor Bosch", status: "ready", available: false,
          used_by_team_id: "t1", used_by_team_name: "Tim Alpha", used_by_requested_team: false }],
      };
    });
    const panel = await within(dialog).findByRole("region", { name: "Aset tim pada tanggal jadwal" });
    expect(await within(panel).findByRole("alert")).toHaveTextContent("Bentrok: dipakai Tim Alpha");
  });

  it("aset bawaan tim yang tersedia pada tanggal itu ditandai Tersedia; aset tim lain tidak tampil", async () => {
    const dialog = await openCreateForBravo((c) => {
      if (c.url === "/assets/tools") return { data: [tool({}), tool({ tool_id: "tl2", name: "Gerinda", team_id: "t1" })] };
      if (c.url === "/assets/vehicles") return { data: [vehicle({})] };
      if (c.url === "/assets/availability") return {
        data: [
          { asset_type: "TOOL", asset_id: "tl1", asset_name: "Bor Bosch", status: "ready", available: true,
            used_by_team_id: null, used_by_team_name: null, used_by_requested_team: false },
          { asset_type: "VEHICLE", asset_id: "v1", asset_name: "Truk Hino", status: "ready", available: true,
            used_by_team_id: null, used_by_team_name: null, used_by_requested_team: false },
        ],
      };
    });
    const panel = await within(dialog).findByRole("region", { name: "Aset tim pada tanggal jadwal" });
    expect(await within(panel).findByText("Bor Bosch", { exact: false })).toBeInTheDocument();
    expect(within(panel).getAllByText("Tersedia")).toHaveLength(2);
    expect(within(panel).queryByText(/Gerinda/)).toBeNull();
    expect(within(panel).queryByRole("alert")).toBeNull();
  });

  it("tanpa aset bawaan, panel menjelaskan belum ada aset tim", async () => {
    const dialog = await openCreateForBravo((c) => {
      if (c.url === "/assets/tools") return { data: [] };
      if (c.url === "/assets/vehicles") return { data: [] };
      if (c.url === "/assets/availability") return { data: [] };
    });
    const panel = await within(dialog).findByRole("region", { name: "Aset tim pada tanggal jadwal" });
    expect(await within(panel).findByText(/Belum ada kendaraan atau alat/)).toBeInTheDocument();
  });
});
