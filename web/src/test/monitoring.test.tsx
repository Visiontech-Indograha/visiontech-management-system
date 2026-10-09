import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const group = {
  id: "p1",
  number: "Rencana Kerja/001",
  title: "Instalasi CCTV",
  status: "IN_PROGRESS",
  unit_id: "u1",
  location_text: "Cikarang",
  period_start: "2026-10-01",
  period_end: "2026-10-05",
  leader: { employee_id: "e1", full_name: "Bu Ketua" },
  total_days: 3,
  approved_days: 1,
  late_days: 1,
  days: [
    { id: "d1", work_date: "2026-10-01", title: "Survei", state: "APPROVED" },
    { id: "d2", work_date: "2026-10-02", title: "Tarik kabel", state: "LATE" },
    { id: "d3", work_date: "2026-10-03", title: "Uji", state: "UPCOMING" },
  ],
};

describe("Timeline tim", () => {
  it("tanpa view:timeline ditolak", () => {
    mockApi(() => undefined);
    const { router } = renderRoute("/timeline", { role: "HR" });
    expect(router.state.location.pathname).toBe("/forbidden");
  });

  it("menampilkan hari dengan label keadaan dan mengirim filter tanggal", async () => {
    const calls = mockApi((c) => (c.url === "/timeline" ? { data: [group] } : undefined));
    renderRoute("/timeline", { role: "PM" });
    const section = await screen.findByRole("region", { name: "Instalasi CCTV" });
    expect(within(section).getByText("Laporan belum dikirim")).toBeInTheDocument();
    expect(within(section).getByText("Selesai & disetujui")).toBeInTheDocument();
    expect(within(section).getByText(/1 laporan terlambat/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Dari tanggal"), { target: { value: "2026-10-01" } });
    await waitFor(() => expect(calls[calls.length - 1].params).toEqual({ from: "2026-10-01" }));
  });

  it("kosong dan galat", async () => {
    mockApi((c) => (c.url === "/timeline" ? { data: [] } : undefined));
    const first = renderRoute("/timeline", { role: "OPS" });
    expect(await screen.findByText("Tidak ada pekerjaan berjalan pada rentang ini.")).toBeInTheDocument();
    first.unmount();
    mockApi(() => apiError(500, "INTERNAL_ERROR", "x"));
    renderRoute("/timeline", { role: "OPS" });
    expect(await screen.findByRole("button", { name: "Coba lagi" })).toBeInTheDocument();
  });
});

describe("Rekap absensi", () => {
  it("menampilkan baris per karyawan dan mengirim bulan", async () => {
    const calls = mockApi((c) =>
      c.url === "/recaps/attendance"
        ? {
            data: {
              month: "2026-10",
              employees: [{ employee_id: "e1", full_name: "Budi", days_present: 20, auto_valid: 18, needs_review: 1, approved: 1, rejected: 0 }],
            },
          }
        : undefined,
    );
    renderRoute("/attendance-recap", { role: "FINANCE" });
    expect((await screen.findAllByText("Budi")).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Bulan"), { target: { value: "2026-09" } });
    await waitFor(() => expect(calls[calls.length - 1].params).toEqual({ month: "2026-09" }));
  });

  it("kosong", async () => {
    mockApi((c) => (c.url === "/recaps/attendance" ? { data: { month: "2026-10", employees: [] } } : undefined));
    renderRoute("/attendance-recap", { role: "field" });
    expect(await screen.findByText("Belum ada catatan kehadiran pada bulan ini.")).toBeInTheDocument();
  });
});
