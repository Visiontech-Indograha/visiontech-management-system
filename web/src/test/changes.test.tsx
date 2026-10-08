import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

/** Alur SK v2 (PR3): adendum diajukan ketua saat SK Berjalan; PM menolak atau menerima dengan mengubah isi SK. */
const plan = {
  id: "p1", title: "Instalasi CCTV", unit_id: "u1", site_id: null, location_text: "Cikarang", description: null,
  period_start: "2026-10-01", period_end: "2026-10-20", pm_employee_id: "e-pm", leader_employee_id: "e-lead",
  number: "Rencana Kerja/001", status: "IN_PROGRESS", revision: 1, row_version: 7, cancellation_reason: null, appeal_reason: null,
};
const change = (status: string) => ({
  id: "c1", change_type: "AMENDMENT", status, reason: "Tambah 1 hari kerja", decision_reason: null,
  created_at: "2026-10-03T01:00:00Z", requested_by_name: "Bu Ketua", decided_by_name: null, document_id: null,
});
const setup = (status: string, extra?: (url: string, method: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "", c.method ?? "get");
    if (hit) return hit;
    if (c.url === "/work-plans/p1") return { data: plan };
    if (c.url === "/work-plans/p1/changes") return { data: [change(status)] };
    if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    if (c.url === "/work-plans/p1/weekly" || c.url === "/work-plans/p1/days") return { data: [] };
  });

describe("Revisi saat rencana kerja Berjalan", () => {
  it("PM melihat usulan ketua dan dapat menerimanya dengan mengubah isi rencana kerja", async () => {
    setup("PENDING_PM");
    renderRoute("/work-plans/p1", { role: "PM" });
    const panel = await screen.findByRole("region", { name: "Permintaan revisi" });
    expect(within(panel).getByText("Tambah 1 hari kerja")).toBeInTheDocument();
    expect(within(panel).getByRole("link", { name: "Revisi rencana kerja" })).toHaveAttribute("href", "/work-plans/p1/amend/c1");
  });

  it("PM menolak revisi dengan catatan", async () => {
    const calls = setup("PENDING_PM", (url, method) =>
      url === "/work-plans/p1/amendments/c1/reject" && method === "post" ? { data: [change("REJECTED")] } : undefined,
    );
    renderRoute("/work-plans/p1", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Tolak permintaan" }));
    const dialog = screen.getByRole("dialog", { name: "Tolak permintaan" });
    fireEvent.change(within(dialog).getByLabelText("Catatan untuk ketua tim"), { target: { value: "Jadwal tidak cukup" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Tolak" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/amendments/c1/reject")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/p1/amendments/c1/reject")!.data).toEqual({ reason: "Jadwal tidak cukup" });
  });

  it("menunggu tanda tangan ketua", async () => {
    setup("AWAITING_LEADER_ACCEPTANCE");
    renderRoute("/work-plans/p1", { role: "PM" });
    expect(await screen.findByText(/Menunggu tanda tangan ketua di HP/)).toBeInTheDocument();
  });
});
