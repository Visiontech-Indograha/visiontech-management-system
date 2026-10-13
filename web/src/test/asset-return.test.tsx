import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { mockApi, renderRoute } from "./utils";

/**
 * R-19 · M6/R9 dari layar: ketua SK peminjam mengembalikan aset, petugas aset memeriksanya.
 * Dulu tidak ada tombolnya sama sekali — siklus aset hanya bisa diselesaikan lewat API.
 */

const asset = (over: Record<string, unknown> = {}) => ({
  id: "a1", kind: "TOOL", vehicle_type: null, code: "TL-01", name: "Tangga lipat", condition: "Baik", status: "IN_USE",
  allocation_id: "al1", work_plan_id: "p1", plan_number: "SK-202609-1a2b3c4d", leader_employee_id: "e-lead",
  pending_return_id: null, return_condition: null, return_note: null, return_requested_by_name: null,
  ...over,
});

const setup = (items: unknown[], extra?: (url: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "");
    if (hit) return hit;
    if (c.url === "/assets") return { data: items };
    if (c.url === "/work-plans") return { data: [] };
    if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
  });

describe("pengembalian aset", () => {
  it("ketua rencana kerja peminjam mengajukan pengembalian dengan kondisi & catatan", async () => {
    const calls = setup([asset()], (url) =>
      url === "/assets/allocations/al1/return" ? { data: { id: "r1", asset_allocation_id: "al1" } } : undefined,
    );
    renderRoute("/assets", { role: "field" }); // karyawan lapangan e-lead = ketua rencana kerja peminjam
    expect(await screen.findByText("Dipakai: rencana kerja SK-202609-1a2b3c4d")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ajukan pengembalian" }));
    const dialog = screen.getByRole("dialog", { name: "Kembalikan Tangga lipat" });
    fireEvent.change(within(dialog).getByLabelText("Catatan (opsional)"), { target: { value: "Selesai dipakai" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajukan pengembalian" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/assets/allocations/al1/return")).toBe(true));
    expect(calls.find((c) => c.url === "/assets/allocations/al1/return")!.data).toEqual({
      condition_on_return: "Baik",
      note: "Selesai dipakai",
    });
  });

  it("bukan ketua rencana kerja peminjam: tidak ada tombol pengembalian", async () => {
    setup([asset({ leader_employee_id: "e-lain" })]);
    renderRoute("/assets", { role: "field" });
    await screen.findByText("Tangga lipat");
    expect(screen.queryByRole("button", { name: "Ajukan pengembalian" })).toBeNull();
  });

  it("petugas aset: tolak wajib beralasan, lalu terkirim", async () => {
    const calls = setup(
      [asset({ status: "RETURN_PENDING", pending_return_id: "r1", return_condition: "Baik", return_note: "Selesai dipakai",
               return_requested_by_name: "Aris Setyawan" })],
      (url) => (url === "/assets/returns/r1/verify" ? { data: { id: "r1" } } : undefined),
    );
    renderRoute("/assets", { role: "ASSET" });
    expect(await screen.findByText(/Pengembalian diajukan Aris Setyawan/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Periksa pengembalian" }));
    const dialog = screen.getByRole("dialog", { name: "Periksa pengembalian Tangga lipat" });
    fireEvent.change(within(dialog).getByLabelText("Hasil pemeriksaan"), { target: { value: "REJECT" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan hasil" }));
    expect(await within(dialog).findByText("Alasan penolakan wajib diisi.")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Catatan (wajib jika ditolak)"), { target: { value: "Anak tangga retak" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan hasil" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/assets/returns/r1/verify")).toBe(true));
    expect(calls.find((c) => c.url === "/assets/returns/r1/verify")!.data).toEqual({ is_accepted: false, note: "Anak tangga retak" });
  });

  it("riwayat pengembalian: BAST bisa diunduh untuk yang sudah diperiksa", async () => {
    URL.createObjectURL = vi.fn(() => "blob:uji");
    URL.revokeObjectURL = vi.fn();
    const calls = setup([asset({ status: "AVAILABLE", allocation_id: null, plan_number: null, leader_employee_id: null })], (url) => {
      if (url === "/assets/a1/returns")
        return {
          data: [
            { id: "r2", plan_number: "SK-2", requested_by_name: "Aris Setyawan", requested_at: "2026-09-27T01:00:00Z",
              condition_on_return: "Baik", note: null, verified_by_name: null, verified_at: null, is_accepted: null },
            { id: "r1", plan_number: "SK-1", requested_by_name: "Aris Setyawan", requested_at: "2026-09-20T01:00:00Z",
              condition_on_return: "Baik", note: "Lengkap", verified_by_name: "Petugas Aset", verified_at: "2026-09-20T03:00:00Z",
              is_accepted: true },
          ],
        };
      if (url === "/assets/returns/r1/pdf") return { data: new Blob(["%PDF"]) };
    });
    renderRoute("/assets", { role: "ASSET" });
    fireEvent.click(await screen.findByRole("button", { name: "Riwayat" }));
    const dialog = screen.getByRole("dialog", { name: "Riwayat pengembalian Tangga lipat" });
    expect(await within(dialog).findByText(/Rencana Kerja SK-1 · Diterima/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Rencana Kerja SK-2 · Menunggu pemeriksaan/)).toBeInTheDocument();
    const buttons = within(dialog).getAllByRole("button", { name: "Unduh BAST" });
    expect(buttons).toHaveLength(1);                    // hanya yang sudah diperiksa
    fireEvent.click(buttons[0]);
    await waitFor(() => expect(calls.some((c) => c.url === "/assets/returns/r1/pdf")).toBe(true));
  });
});

