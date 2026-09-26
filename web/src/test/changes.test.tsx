import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { mockApi, renderRoute } from "./utils";

/** PM yang juga ditunjuk sebagai ketua pada SK ini — sah melakukan tindakan ketua. */
const pmAsLeader = () => ({ ...mockMe("PM")!, employee_id: "e-lead" });

const plan = {
  id: "p1",
  title: "Instalasi CCTV",
  unit_id: "u1",
  site_id: null,
  location_text: "Cikarang",
  description: null,
  period_start: "2026-10-01",
  period_end: "2026-10-20",
  pm_employee_id: "e-pm",
  leader_employee_id: "e-lead",
  number: "SK/001",
  status: "IN_PROGRESS",
  revision: 0,
  row_version: 7,
  cancellation_reason: null,
  appeal_reason: null,
};
const emp = (id: string, name: string) => ({ id, employee_no: id, full_name: name, position: "Teknisi", join_date: "2024-01-01", unit_id: "u1", is_active: true });
const change = (over: Record<string, unknown> = {}) => ({
  id: "c1",
  work_plan_id: "p1",
  change_type: "EXTEND",
  status: "PENDING_PM",
  reason: "Cuaca buruk",
  decision_reason: null,
  ...over,
});

const setup = (extra?: (url: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "");
    if (hit) return hit;
    if (c.url === "/work-plans/p1") return { data: plan };
    if (c.url === "/employees") return { data: { items: [emp("e-lead", "Bu Ketua"), emp("e-a", "Andi")], total: 2, page: 1, size: 100 } };
    if (c.url === "/work-plans/p1/weekly") return { data: [] };
  });

describe("Usulan perubahan SK", () => {
  it("ketua mengajukan perpanjangan; tanggal harus setelah akhir rencana", async () => {
    const calls = setup((url) => (url === "/work-plans/p1/changes" ? { status: 201, data: change() } : undefined));
    renderRoute("/work-plans/p1", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Ajukan perpanjangan" }));
    const dialog = screen.getByRole("dialog", { name: "Ajukan perpanjangan" });
    fireEvent.change(within(dialog).getByLabelText("Tanggal akhir baru"), { target: { value: "2026-10-10" } });
    fireEvent.change(within(dialog).getByLabelText("Alasan"), { target: { value: "Cuaca buruk" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajukan perpanjangan" }));
    expect(await within(dialog).findByText("Tanggal akhir baru harus setelah akhir rencana saat ini.")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Tanggal akhir baru"), { target: { value: "2026-10-25" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajukan perpanjangan" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(calls.find((c) => c.url === "/work-plans/p1/changes")!.data).toEqual({
      type: "EXTEND",
      new_period_end: "2026-10-25",
      reason: "Cuaca buruk",
    });
    // Usulan hasil respons tampil dengan statusnya.
    expect(screen.getByRole("region", { name: "Usulan perubahan" })).toHaveTextContent("Menunggu PM");
  });

  it("PM mengajukan adendum personel lalu menariknya", async () => {
    const calls = setup((url) => {
      if (url === "/work-plans/p1/changes")
        return { status: 201, data: change({ change_type: "PERSONNEL", status: "AWAITING_LEADER_ACCEPTANCE", reason: "Rotasi" }) };
      if (url === "/changes/c1/withdraw")
        return { data: change({ change_type: "PERSONNEL", status: "WITHDRAWN", reason: "Rotasi", decision_reason: "Batal rotasi" }) };
    });
    renderRoute("/work-plans/p1", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Adendum personel" }));
    const dialog = screen.getByRole("dialog", { name: "Adendum personel" });
    fireEvent.click(await within(dialog).findByLabelText(/Andi/));
    fireEvent.change(within(dialog).getByLabelText("Alasan"), { target: { value: "Rotasi" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajukan adendum" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(calls.find((c) => c.url === "/work-plans/p1/changes")!.data).toEqual({
      type: "PERSONNEL",
      reason: "Rotasi",
      leader_employee_id: "e-lead",
      member_employee_ids: ["e-a"],
    });

    fireEvent.click(screen.getByRole("button", { name: "Tarik adendum personel" }));
    const ask = screen.getByRole("dialog", { name: "Tarik adendum personel" });
    fireEvent.change(within(ask).getByLabelText("Alasan"), { target: { value: "Batal rotasi" } });
    fireEvent.click(within(ask).getByRole("button", { name: "Tarik adendum personel" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/changes/c1/withdraw")).toBe(true));
    expect(calls.find((c) => c.url === "/changes/c1/withdraw")!.data).toEqual({ reason: "Batal rotasi" });
    expect(await screen.findByText("Ditarik PM")).toBeInTheDocument();
  });

  it("PM menyetujui perpanjangan yang baru diajukan", async () => {
    const calls = setup((url) => {
      if (url === "/work-plans/p1/changes") return { status: 201, data: change() };
      if (url === "/changes/c1/approve") return { data: change({ status: "AWAITING_LEADER_ACCEPTANCE" }) };
    });
    renderRoute("/work-plans/p1", { me: pmAsLeader() });
    fireEvent.click(await screen.findByRole("button", { name: "Ajukan perpanjangan" }));
    const dialog = screen.getByRole("dialog", { name: "Ajukan perpanjangan" });
    fireEvent.change(within(dialog).getByLabelText("Tanggal akhir baru"), { target: { value: "2026-10-25" } });
    fireEvent.change(within(dialog).getByLabelText("Alasan"), { target: { value: "Cuaca" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajukan perpanjangan" }));
    fireEvent.click(await screen.findByRole("button", { name: "Setujui perpanjangan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/changes/c1/approve")).toBe(true));
    expect(await screen.findByText("Menunggu ketua")).toBeInTheDocument();
  });
});
