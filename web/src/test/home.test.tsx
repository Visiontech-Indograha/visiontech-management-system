import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

/** Beranda: ringkasan jadwal harian minggu ini & absensi yang perlu diperiksa. */

const todayIso = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
const plan = (id: string, status: string, work_date = todayIso) => ({
  daily_plan_id: id, division_id: "d1", division_name: "Sipil", team_id: `t-${id}`, team_name: `Tim ${id}`,
  leader_employee_id: "e-lead", leader_name: "Agus", work_date, site_name: `Site ${id}`, site_lat: "1", site_lng: "1",
  attendance_radius_m: 150, clock_in_time: "07:00:00", clock_out_time: "16:00:00", status, created_by_id: "e-pm",
  item_count: 0, done_count: 0,
});

const stat = (label: string) => screen.getByText(label).closest("a")!;

describe("beranda", () => {
  it("menghitung jadwal hari ini, berjalan, dan menunggu persetujuan; daftar maksimal 6", async () => {
    const plans = [
      plan("a", "ONGOING"), plan("b", "ONGOING"), plan("c", "APPROVED"), plan("d", "SUBMITTED", "2099-01-01"),
      plan("e", "SUBMITTED", "2099-01-01"), plan("f", "DRAFT", "2099-01-01"),
    ];
    mockApi((c) => {
      if (c.url === "/work-plans/daily") return { data: plans };
      if (c.url === "/attendance") return { data: { items: [], total: 4, page: 1, size: 1 } };
    });
    renderRoute("/", { role: "PM" });

    expect(await screen.findByText("Tim a")).toBeInTheDocument();
    expect(within(stat("Jadwal hari ini")).getByText("3")).toBeInTheDocument();
    expect(within(stat("Jadwal sedang berjalan")).getByText("2")).toBeInTheDocument();
    expect(within(stat("Jadwal menunggu persetujuan")).getByText("2")).toBeInTheDocument();
    expect(await within(stat("Absensi perlu diperiksa")).findByText("4")).toBeInTheDocument();
    expect(screen.queryByText("Tim f")).toBeNull();                           // draf tidak termasuk aktif
  });

  it("karyawan lapangan tidak melihat kartu pemeriksaan absensi dan tidak memanggil /attendance", async () => {
    const calls = mockApi((c) => (c.url === "/work-plans/daily" ? { data: [] } : undefined));
    renderRoute("/", { role: "field" });
    expect(await screen.findByText("Belum ada jadwal aktif.")).toBeInTheDocument();
    expect(screen.queryByText("Absensi perlu diperiksa")).toBeNull();
    expect(calls.some((c) => c.url === "/attendance")).toBe(false);
  });

  it("galat memuat jadwal: pesan galat, bukan 'Belum ada jadwal aktif'", async () => {
    mockApi(() => apiError(500, "INTERNAL_ERROR", "Terjadi kesalahan."));
    renderRoute("/", { role: "field" });
    expect(await screen.findByText("Jadwal tidak dapat dimuat.")).toBeInTheDocument();
    expect(screen.queryByText("Belum ada jadwal aktif.")).toBeNull();
  });

  it("HR: dokumen mendekati kedaluwarsa (≤ 30 hari / lewat) tampil", async () => {
    const doc = (id: string, urgency: string, days: number) => ({
      id, employee_id: `emp-${id}`, full_name: `Karyawan ${id}`, doc_type: "SIM A",
      expiry_date: "2026-10-01", days_left: days, urgency,
    });
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily") return { data: [] };
      if (c.url === "/documents/expiring")
        return { data: { items: [doc("a", "EXPIRED", -2), doc("b", "CRITICAL", 3), doc("c", "WARNING", 20)] } };
    });
    renderRoute("/", { role: "HR" });

    const card = (await screen.findByText("Dokumen mendekati kedaluwarsa", { selector: "[data-slot=card-title]" })).closest("[data-slot=card]") as HTMLElement;
    const statLink = screen.getByRole("link", { name: /Dokumen mendekati kedaluwarsa/ });
    expect(statLink).toHaveAttribute("href", "/directory");
    expect(await within(statLink).findByText("3")).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: /Karyawan a/ })).toHaveAttribute("href", "/directory/emp-a");
    expect(within(card).getByText("Kedaluwarsa")).toBeInTheDocument();
    expect(within(card).getByText("≤ 7 hari")).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/documents/expiring")).toBe(true);
  });

  it("tanpa izin kelola dokumen: tidak memanggil /documents/expiring", async () => {
    const calls = mockApi((c) => (c.url === "/work-plans/daily" ? { data: [] } : undefined));
    renderRoute("/", { role: "PM" });
    await screen.findByText("Belum ada jadwal aktif.");
    expect(calls.some((c) => c.url === "/documents/expiring")).toBe(false);
  });
});

