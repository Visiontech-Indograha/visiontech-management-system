import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

const row = (over: Record<string, unknown> = {}) => ({
  id: "a1",
  employee_id: "e1",
  work_date: "2026-10-02",
  site_id: "s1",
  site_label: "Gudang Cikarang",
  check_in_at: "2026-10-02T00:30:00Z",
  check_out_at: null,
  distance_m: 180.4,
  is_late: false,
  is_early_leave: false,
  status: "NEEDS_REVIEW",
  explanation: null,
  reviewed_at: null,
  employee_name: "Budi",
  selfie_file_id: null,
  can_review: true, // R-33: tombol Tinjau mengikuti penanda server
  ...over,
});
const employees = { items: [{ id: "e1", full_name: "Budi", position: "Teknisi", employee_no: "1", join_date: "2024-01-01", is_active: true }], total: 1, page: 1, size: 100 };

const setup = (extra?: (url: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "");
    if (hit) return hit;
    if (c.url === "/attendance") return { data: { items: [row()], total: 1, page: 1, size: 50 } };
    if (c.url === "/employees") return { data: employees };
  });

describe("Absensi", () => {
  it("Finance: default filter perlu review, tinjau wajib catatan", async () => {
    const calls = setup((url) => (url === "/attendance/a1/review" ? { data: { message: "Absensi di-approved." } } : undefined));
    renderRoute("/attendance", { role: "FINANCE" });
    expect(await screen.findByText("Gudang Cikarang", { exact: false })).toBeInTheDocument();
    expect(calls.find((c) => c.url === "/attendance")!.params).toMatchObject({ status: "NEEDS_REVIEW", page: 1, size: 50 });
    fireEvent.click(screen.getByRole("button", { name: "Tinjau" }));
    const dialog = screen.getByRole("dialog", { name: "Tinjau absensi" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan keputusan" }));
    expect(await within(dialog).findByText("Catatan pemeriksaan wajib diisi.")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Catatan pemeriksaan"), { target: { value: "Lokasi proyek baru" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan keputusan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/attendance/a1/review")).toBe(true));
    expect(calls.find((c) => c.url === "/attendance/a1/review")!.data).toEqual({ is_approved: true, note: "Lokasi proyek baru" });
  });

  it("karyawan memberi penjelasan", async () => {
    // Absensi milik sendiri (karyawan tiruan "e-lead"), bukan wewenang tinjau.
    const own = { data: { items: [row({ employee_id: "e-lead", can_review: false })], total: 1, page: 1, size: 50 } };
    const calls = setup((url) =>
      url === "/attendance/a1/explain" ? { data: { message: "Penjelasan ditambahkan." } } : url === "/attendance" ? own : undefined,
    );
    renderRoute("/attendance", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Beri penjelasan" }));
    const dialog = screen.getByRole("dialog", { name: "Beri penjelasan" });
    fireEvent.change(within(dialog).getByLabelText("Penjelasan"), { target: { value: "GPS melenceng" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kirim penjelasan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/attendance/a1/explain")).toBe(true));
    expect(calls.find((c) => c.url === "/attendance/a1/explain")!.data).toEqual({ explanation: "GPS melenceng" });
  });

  it("kosong", async () => {
    mockApi((c) => (c.url === "/attendance" ? { data: { items: [], total: 0, page: 1, size: 50 } } : c.url === "/employees" ? { data: employees } : undefined));
    renderRoute("/attendance", { role: "field" });
    expect(await screen.findByText("Tidak ada catatan kehadiran yang cocok.")).toBeInTheDocument();
  });
});
