import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

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
const ot = (over: Record<string, unknown> = {}) => ({
  id: "o1",
  work_plan_id: "p1",
  plan_document_id: null,
  employee_id: "e-lead",
  work_date: "2026-10-03",
  hours: 2,
  reason: "Pengecoran malam",
  status: "PENDING_PM",
  reviewed_by: null,
  reviewed_at: null,
  review_note: null,
  created_at: "2026-10-03T12:00:00Z",
  ...over,
});
const employees = { items: [{ id: "e-lead", full_name: "Bu Ketua", position: "Teknisi", employee_no: "1", join_date: "2024-01-01", is_active: true }], total: 1, page: 1, size: 100 };

const setup = (list: unknown[], extra?: (url: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "");
    if (hit) return hit;
    if (c.url === "/work-plans/p1") return { data: plan };
    if (c.url === "/employees") return { data: employees };
    if (c.url === "/work-plans/p1/weekly") return { data: [] };
    if (c.url === "/overtime" && c.method === "get") return { data: list };
  });

describe("Lembur", () => {
  it("anggota mengajukan lembur; jam divalidasi 0–12", async () => {
    mockApi((c) => {
      if (c.url === "/overtime" && c.method === "post") return { status: 201, data: ot() };
      if (c.url === "/work-plans/p1") return { data: plan };
      if (c.url === "/employees") return { data: employees };
      if (c.url === "/work-plans/p1/weekly") return { data: [] };
      if (c.url === "/overtime") return { data: [] };
    });
    renderRoute("/work-plans/p1", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Ajukan Lembur" }));
    const dialog = screen.getByRole("dialog", { name: "Ajukan Lembur" });
    fireEvent.change(within(dialog).getByLabelText("Jumlah jam"), { target: { value: "13" } });
    fireEvent.change(within(dialog).getByLabelText("Alasan"), { target: { value: "Pengecoran malam" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajukan lembur" }));
    expect(await within(dialog).findByText("Jam lembur harus lebih dari 0 dan paling banyak 12.")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Jumlah jam"), { target: { value: "2.5" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajukan lembur" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("mengirim OvertimeCreate dengan hours angka", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/overtime" && c.method === "post") return { status: 201, data: ot() };
      if (c.url === "/work-plans/p1") return { data: plan };
      if (c.url === "/employees") return { data: employees };
      if (c.url === "/work-plans/p1/weekly") return { data: [] };
      if (c.url === "/overtime") return { data: [] };
    });
    renderRoute("/work-plans/p1", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Ajukan Lembur" }));
    const dialog = screen.getByRole("dialog", { name: "Ajukan Lembur" });
    fireEvent.change(within(dialog).getByLabelText("Jumlah jam"), { target: { value: "2.5" } });
    fireEvent.change(within(dialog).getByLabelText("Alasan"), { target: { value: "Pengecoran malam" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajukan lembur" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/overtime")).toBe(true));
    expect(calls.find((c) => c.method === "post" && c.url === "/overtime")!.data).toEqual({
      work_plan_id: "p1",
      hours: 2.5,
      reason: "Pengecoran malam",
    });
  });

  it("PM meninjau lembur PENDING_PM dari panel SK", async () => {
    const calls = setup([ot()], (url) => (url === "/overtime/o1/review" ? { data: ot({ status: "APPROVED" }) } : undefined));
    renderRoute("/work-plans/p1", { role: "PM" });
    const panel = await screen.findByRole("region", { name: "Rekap Lembur" });
    expect(await within(panel).findByText("Bu Ketua")).toBeInTheDocument();
    fireEvent.click(within(panel).getByRole("button", { name: "Tinjau lembur" }));
    const dialog = screen.getByRole("dialog", { name: "Tinjau lembur" });
    fireEvent.change(within(dialog).getByLabelText("Keputusan"), { target: { value: "REJECTED" } });
    fireEvent.change(within(dialog).getByLabelText("Catatan (opsional)"), { target: { value: "Tidak mendesak" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan keputusan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/overtime/o1/review")).toBe(true));
    expect(calls.find((c) => c.url === "/overtime/o1/review")!.data).toEqual({ decision: "REJECTED", note: "Tidak mendesak" });
  });

  it("Finance melihat lembur SK tetapi tidak dapat meninjau (hanya PM unit/OPS)", async () => {
    setup([ot()]);
    renderRoute("/work-plans/p1", { role: "FINANCE" });
    const panel = await screen.findByRole("region", { name: "Rekap Lembur" });
    expect(await within(panel).findByText("Bu Ketua")).toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: "Tinjau lembur" })).toBeNull();
  });

  it("rekap lembur bulanan", async () => {
    const calls = mockApi((c) =>
      c.url === "/recaps/overtime"
        ? { data: [{ employee_id: "e1", employee_name: "Budi", period_month: "2026-10-01", approved_entries: 2, pending_entries: 1, approved_hours: 5.5 }] }
        : undefined,
    );
    renderRoute("/overtime-recap", { role: "FINANCE" });
    expect(await screen.findByText("Budi")).toBeInTheDocument();
    expect(screen.getByText("5.5")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Bulan"), { target: { value: "2026-09" } });
    await waitFor(() => expect(calls[calls.length - 1].params).toEqual({ month: "2026-09" }));
  });

  it("rekap lembur ditolak untuk karyawan biasa", () => {
    mockApi(() => undefined);
    const { router } = renderRoute("/overtime-recap", { role: "field" });
    expect(router.state.location.pathname).toBe("/forbidden");
  });
});
