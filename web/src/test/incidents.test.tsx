import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

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
const incident = (over: Record<string, unknown> = {}) => ({
  id: "i1",
  work_plan_id: "p1",
  reported_by: "e-lead",
  occurred_on: "2026-10-03",
  category: "K3_RINGAN",
  severity: "SEDANG",
  description: "Tangan tergores",
  status: "OPEN",
  resolved_by: null,
  resolved_at: null,
  resolution_note: null,
  created_at: "2026-10-03T02:00:00Z",
  ...over,
});

const setup = (extra?: (url: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    // Daftar insiden SK (GET) — kosong di awal; POST ditangani `extra`.
    if (c.url === "/hse/incidents" && (c.method ?? "get").toLowerCase() === "get") return { data: [] };
    const hit = extra?.(c.url ?? "");
    if (hit) return hit;
    if (c.url === "/work-plans/p1") return { data: plan };
    if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    if (c.url === "/work-plans/p1/weekly") return { data: [] };
  });

const report = async () => {
  fireEvent.click(await screen.findByRole("button", { name: "Lapor Insiden/HSE" }));
  const dialog = screen.getByRole("dialog", { name: "Lapor Insiden/HSE" });
  fireEvent.change(within(dialog).getByLabelText("Kategori"), { target: { value: "K3_RINGAN" } });
  fireEvent.change(within(dialog).getByLabelText("Tingkat keparahan"), { target: { value: "SEDANG" } });
  fireEvent.change(within(dialog).getByLabelText("Uraian kejadian"), { target: { value: "Tangan tergores" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Kirim laporan" }));
  return dialog;
};

describe("Insiden / HSE", () => {
  it("validasi lalu kirim POST /hse/incidents", async () => {
    const calls = setup((url) => (url === "/hse/incidents" ? { status: 201, data: incident() } : undefined));
    renderRoute("/work-plans/p1", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Lapor Insiden/HSE" }));
    const dialog = screen.getByRole("dialog", { name: "Lapor Insiden/HSE" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kirim laporan" }));
    expect(await within(dialog).findByText("Pilih kategori.")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Batal" }));
    await report();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(calls.find((c) => c.url === "/hse/incidents" && c.method === "post")!.data).toEqual({
      work_plan_id: "p1",
      category: "K3_RINGAN",
      severity: "SEDANG",
      description: "Tangan tergores",
      evidence_file_ids: [],
    });
    expect(screen.getByRole("region", { name: "Laporan Insiden / HSE" })).toHaveTextContent("[K3 ringan] Sedang");
    expect(screen.queryByRole("button", { name: "Selesaikan" })).toBeNull();
  });

  it("penolakan API tampil di dialog", async () => {
    setup((url) => (url === "/hse/incidents" ? apiError(403, "FORBIDDEN", "Hanya ketua atau anggota tim pekerjaan ini yang dapat melakukan tindakan ini.") : undefined));
    renderRoute("/work-plans/p1", { role: "PM" });
    const dialog = await report();
    expect(await within(dialog).findByText(/Hanya ketua atau anggota tim/)).toBeInTheDocument();
  });

  it("PM menyelesaikan insiden dengan catatan", async () => {
    const calls = setup((url) => {
      if (url === "/hse/incidents") return { status: 201, data: incident() };
      if (url === "/hse/incidents/i1/resolve") return { data: incident({ status: "RESOLVED", resolution_note: "Sudah diobati" }) };
    });
    renderRoute("/work-plans/p1", { role: "PM" });
    await report();
    fireEvent.click(await screen.findByRole("button", { name: "Selesaikan" }));
    const dialog = screen.getByRole("dialog", { name: "Selesaikan insiden" });
    fireEvent.change(within(dialog).getByLabelText("Catatan penyelesaian"), { target: { value: "Sudah diobati" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Selesaikan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/hse/incidents/i1/resolve")).toBe(true));
    expect(calls.find((c) => c.url === "/hse/incidents/i1/resolve")!.data).toEqual({ resolution_note: "Sudah diobati" });
    expect(await screen.findByText("Penyelesaian: Sudah diobati")).toBeInTheDocument();
  });
});
