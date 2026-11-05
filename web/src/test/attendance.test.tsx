import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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
    expect(calls.find((c) => c.url === "/attendance")!.params).toMatchObject({ status: "NEEDS_REVIEW", size: 50 });
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

  it("R-34: absen offline ditandai di daftar & dialog tinjau menampilkan catatan server dan jam pulang yang ditahan", async () => {
    const offline = {
      data: {
        items: [
          row({
            offline: true,
            offline_note: "jam hanya dari satelit GPS (HP dinyalakan ulang saat offline)",
            check_out_requested_at: "2026-10-02T02:33:45Z",
          }),
        ],
        total: 1,
        page: 1,
        size: 50,
      },
    };
    setup((url) => (url === "/attendance" ? offline : undefined));
    renderRoute("/attendance", { role: "PM" });
    expect(await screen.findByText(/· absen offline/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tinjau" }));
    const dialog = screen.getByRole("dialog", { name: "Tinjau absensi" });
    const notice = within(dialog).getByRole("status");
    expect(notice).toHaveTextContent("Absen offline (direkam tanpa sinyal, dikirim saat online)");
    expect(notice).toHaveTextContent("Catatan server: jam hanya dari satelit GPS (HP dinyalakan ulang saat offline)");
    expect(notice).toHaveTextContent(/Absen pulang 02 Okt 2026 09\.33 WIB berlaku bila absensi ini disetujui\./);
  });

  it("dialog tinjau menampilkan foto bukti terpisah tanpa label wajah", async () => {
    setup((url) =>
      url === "/attendance"
        ? { data: { items: [row({ evidence_photo_file_id: "f-bukti" })], total: 1, page: 1, size: 50 } }
        : undefined,
    );
    renderRoute("/attendance", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Tinjau" }));
    const dialog = screen.getByRole("dialog", { name: "Tinjau absensi" });
    expect(within(dialog).getByText("Foto bukti")).toBeInTheDocument();
    expect(within(dialog).queryByText("Verifikasi Wajah (Server)")).not.toBeInTheDocument();
  });

  it("absen online biasa tidak memunculkan tanda offline", async () => {
    setup();
    renderRoute("/attendance", { role: "PM" });
    expect(await screen.findByText("Gudang Cikarang", { exact: false })).toBeInTheDocument();
    expect(screen.queryByText(/absen offline/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tinjau" }));
    expect(within(screen.getByRole("dialog", { name: "Tinjau absensi" })).queryByRole("status")).not.toBeInTheDocument();
  });

  it("kosong", async () => {
    mockApi((c) => (c.url === "/attendance" ? { data: { items: [], total: 0, page: 1, size: 50 } } : c.url === "/employees" ? { data: employees } : undefined));
    renderRoute("/attendance", { role: "field" });
    expect(await screen.findByText("Tidak ada catatan kehadiran yang cocok.")).toBeInTheDocument();
  });

  it("PM: absensi pribadi dipisah dari absensi anggota lewat tab (scope mine/team)", async () => {
    const calls = mockApi((c) => (c.url === "/attendance" ? { data: { items: [], total: 0, page: 1, size: 50 } } : undefined));
    renderRoute("/attendance", { role: "PM" });
    const team = await screen.findByRole("tab", { name: "Absensi anggota" });
    expect(team).toHaveAttribute("aria-selected", "true");               // PM meninjau anggota lebih dulu
    await waitFor(() => expect(calls.some((c) => c.url === "/attendance" && (c.params as { scope?: string })?.scope === "team")).toBe(true));
    fireEvent.click(screen.getByRole("tab", { name: "Absensi saya" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/attendance" && (c.params as { scope?: string })?.scope === "mine")).toBe(true));
  });

  it("Finance/OPS: tab bernama Semua karyawan; pekerja biasa tanpa tab", async () => {
    mockApi((c) => (c.url === "/attendance" ? { data: { items: [], total: 0, page: 1, size: 50 } } : undefined));
    const { unmount } = renderRoute("/attendance", { role: "OPS" });
    expect(await screen.findByRole("tab", { name: "Semua karyawan" })).toBeInTheDocument();
    unmount();
    renderRoute("/attendance", { role: "field" });
    await screen.findByRole("heading", { name: "Absensi" });
    expect(screen.queryByRole("tab")).toBeNull();
  });

  it("Finance: ekspor CSV memakai rentang tanggal dan menolak rentang terbalik", async () => {
    const calls = setup((url) => (url === "/attendance/export" ? { data: "Tanggal,NIK" } : undefined));
    renderRoute("/attendance", { role: "FINANCE" });
    await screen.findByText("Gudang Cikarang", { exact: false });
    const panel = screen.getByRole("form", { name: "Ekspor CSV absensi" });
    fireEvent.change(within(panel).getByLabelText("Ekspor dari"), { target: { value: "2026-10-10" } });
    fireEvent.change(within(panel).getByLabelText("Ekspor sampai"), { target: { value: "2026-10-01" } });
    fireEvent.click(within(panel).getByRole("button", { name: "Ekspor CSV" }));
    expect(await within(panel).findByRole("alert")).toHaveTextContent("Tanggal mulai tidak boleh setelah tanggal akhir.");
    expect(calls.some((c) => c.url === "/attendance/export")).toBe(false);

    fireEvent.change(within(panel).getByLabelText("Ekspor sampai"), { target: { value: "2026-10-31" } });
    window.URL.createObjectURL = vi.fn(() => "blob:x");
    fireEvent.click(within(panel).getByRole("button", { name: "Ekspor CSV" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/attendance/export")).toBe(true));
    const req = calls.find((c) => c.url === "/attendance/export")!;
    expect(req.params).toEqual({ start_date: "2026-10-10", end_date: "2026-10-31" });
  });

  it("peran tanpa export:attendance tidak melihat tombol ekspor CSV", async () => {
    setup();
    renderRoute("/attendance", { role: "field" });
    await screen.findByRole("heading", { name: "Absensi" });
    expect(screen.queryByRole("form", { name: "Ekspor CSV absensi" })).toBeNull();
  });
});
