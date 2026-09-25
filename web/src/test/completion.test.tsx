import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const plan = (status: string) => ({
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
  status,
  revision: 0,
  row_version: 7,
  cancellation_reason: null,
  appeal_reason: null,
});

const setup = (status: string, extra?: (url: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "");
    if (hit) return hit;
    if (c.url === "/work-plans/p1") return { data: plan(status) };
    if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    if (c.url === "/work-plans/p1/weekly") return { data: [] };
  });

describe("Penyelesaian SK", () => {
  it("ketua mengunggah lampiran lalu mengajukan penyelesaian dengan file_id", async () => {
    const calls = setup("IN_PROGRESS", (url) => {
      if (url === "/files/upload") return { data: { file_id: "f9", message: "Berkas berhasil diunggah." } };
      if (url === "/work-plans/p1/request-completion") return { data: plan("COMPLETION_REVIEW") };
    });
    renderRoute("/work-plans/p1", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Buat Laporan Akhir" }));
    const dialog = screen.getByRole("dialog", { name: "Laporan akhir" });
    fireEvent.change(within(dialog).getByLabelText("Laporan Keseluruhan"), { target: { value: "Selesai terpasang" } });
    fireEvent.change(within(dialog).getByLabelText("Ringkasan Kendala Keseluruhan (Wajib)"), { target: { value: "Tidak ada" } });
    const input = within(dialog).getByLabelText("Lampiran (Foto/PDF) (Opsional)");
    Object.defineProperty(input, "files", { value: [new File(["x"], "foto.png", { type: "image/png" })] });
    fireEvent.change(input);
    fireEvent.click(within(dialog).getByRole("button", { name: "Kirim Laporan Akhir (Ajukan Selesai)" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(calls.find((c) => c.url === "/work-plans/p1/request-completion")!.data).toEqual({
      row_version: 7,
      body: "Selesai terpasang",
      obstacle: "Tidak ada",
      evidence_file_ids: ["f9"],
    });
  });

  it("syarat yang ditolak API tampil di dialog", async () => {
    setup("IN_PROGRESS", (url) =>
      url === "/work-plans/p1/request-completion"
        ? apiError(409, "INVALID_STATE", "Seluruh laporan harian wajib disetujui PM terlebih dahulu.")
        : undefined,
    );
    renderRoute("/work-plans/p1", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Buat Laporan Akhir" }));
    const dialog = screen.getByRole("dialog", { name: "Laporan akhir" });
    fireEvent.change(within(dialog).getByLabelText("Laporan Keseluruhan"), { target: { value: "a" } });
    fireEvent.change(within(dialog).getByLabelText("Ringkasan Kendala Keseluruhan (Wajib)"), { target: { value: "b" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kirim Laporan Akhir (Ajukan Selesai)" }));
    expect(await within(dialog).findByText("Seluruh laporan harian wajib disetujui PM terlebih dahulu.")).toBeInTheDocument();
  });

  it("PM menyetujui dan mengembalikan penyelesaian", async () => {
    const calls = setup("COMPLETION_REVIEW", (url) => {
      if (url === "/work-plans/p1/return-completion") return { data: plan("IN_PROGRESS") };
      if (url === "/work-plans/p1/approve-completion") return { data: plan("COMPLETED") };
    });
    renderRoute("/work-plans/p1", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Kembalikan penyelesaian" }));
    const dialog = screen.getByRole("dialog", { name: "Kembalikan penyelesaian" });
    fireEvent.change(within(dialog).getByLabelText("Alasan pengembalian"), { target: { value: "Foto kurang" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kembalikan penyelesaian" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/return-completion")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/p1/return-completion")!.data).toEqual({ row_version: 7, reason: "Foto kurang" });
  });

  it("PM menyetujui penyelesaian", async () => {
    const calls = setup("COMPLETION_REVIEW", (url) =>
      url === "/work-plans/p1/approve-completion" ? { data: plan("COMPLETED") } : undefined,
    );
    renderRoute("/work-plans/p1", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Setujui penyelesaian" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/approve-completion")).toBe(true));
    expect(await screen.findByText("Selesai", { selector: "span" })).toBeInTheDocument();
  });
});
