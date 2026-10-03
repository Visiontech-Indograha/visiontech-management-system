import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

/** Alur SK v2 (PR3): laporan akhir diajukan ketua di HP; PM menyetujui (dengan konfirmasi) atau mengembalikan. */
const plan = (status: string) => ({
  id: "p1", title: "Instalasi CCTV", unit_id: "u1", site_id: null, location_text: "Cikarang", description: null,
  period_start: "2026-10-01", period_end: "2026-10-20", pm_employee_id: "e-pm", leader_employee_id: "e-lead",
  number: "SK/001", status, revision: 1, row_version: 7, cancellation_reason: null, appeal_reason: null,
});

const setup = (status: string, extra?: (url: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "");
    if (hit) return hit;
    if (c.url === "/work-plans/p1") return { data: plan(status) };
    if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    if (c.url === "/work-plans/p1/weekly" || c.url === "/work-plans/p1/days" || c.url === "/work-plans/p1/changes") return { data: [] };
  });

describe("Penutupan SK", () => {
  it("tombol laporan akhir & perpanjangan tidak lagi ada di web (ketua memakai HP)", async () => {
    setup("IN_PROGRESS");
    renderRoute("/work-plans/p1", { role: "field" });
    await screen.findByText("SK/001");
    expect(screen.queryByRole("button", { name: "Buat Laporan Akhir" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Ajukan perpanjangan" })).toBeNull();
  });

  it("PM menyetujui penutupan lewat dialog konfirmasi", async () => {
    const calls = setup("COMPLETION_REVIEW", (url) =>
      url === "/work-plans/p1/approve-completion" ? { data: plan("COMPLETED") } : undefined,
    );
    renderRoute("/work-plans/p1", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Setujui penutupan" }));
    expect(calls.find((c) => c.url === "/work-plans/p1/approve-completion")).toBeUndefined();
    const dialog = screen.getByRole("dialog", { name: "Setujui penutupan?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ya, setujui" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/approve-completion")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/p1/approve-completion")!.data).toEqual({ row_version: 7, reason: "" });
  });

  it("PM mengembalikan dengan catatan untuk ketua", async () => {
    const calls = setup("COMPLETION_REVIEW", (url) =>
      url === "/work-plans/p1/return-completion" ? { data: plan("IN_PROGRESS") } : undefined,
    );
    renderRoute("/work-plans/p1", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Kembalikan (perlu perbaikan)" }));
    const dialog = screen.getByRole("dialog", { name: "Kembalikan (perlu perbaikan)" });
    fireEvent.change(within(dialog).getByLabelText("Catatan untuk ketua tim"), { target: { value: "Lampirkan BAST" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kembalikan (perlu perbaikan)" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/return-completion")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/p1/return-completion")!.data).toEqual({ row_version: 7, reason: "Lampirkan BAST" });
  });
});
