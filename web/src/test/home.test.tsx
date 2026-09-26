import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

/** Beranda: ringkasan SK & absensi yang perlu diperiksa (4 keadaan: memuat, kosong, galat, berhasil). */

const plan = (id: string, status: string) => ({
  id, title: `SK ${id}`, unit_id: "u1", site_id: null, location_text: "Dumai", description: null,
  period_start: "2026-09-01", period_end: "2026-09-30", pm_employee_id: "e-pm", leader_employee_id: "e-lead",
  number: null, status, revision: 0, row_version: 1, cancellation_reason: null, appeal_reason: null,
});

const stat = (label: string) => screen.getByText(label).closest("a")!;

describe("beranda", () => {
  it("menghitung SK berjalan & menunggu, menampilkan maksimal 6 pekerjaan aktif", async () => {
    const plans = [
      plan("a", "IN_PROGRESS"), plan("b", "IN_PROGRESS"), plan("c", "PUBLISHED"), plan("d", "DRAFT"),
      plan("e", "ACCEPTED"), plan("f", "APPEALED"), plan("g", "COMPLETION_REVIEW"), plan("h", "COMPLETED"),
      plan("i", "CANCELLED"),
    ];
    mockApi((c) => {
      if (c.url === "/work-plans") return { data: plans };
      if (c.url === "/attendance") return { data: { items: [], total: 4, page: 1, size: 1 } };
    });
    renderRoute("/", { role: "PM" });

    expect(await screen.findByText("SK a")).toBeInTheDocument();
    expect(within(stat("SK berjalan")).getByText("2")).toBeInTheDocument();
    expect(within(stat("SK menunggu tindakan")).getByText("5")).toBeInTheDocument();
    expect(await within(stat("Absensi perlu diperiksa")).findByText("4")).toBeInTheDocument();
    const list = screen.getByText("Pekerjaan aktif").closest("[data-slot=card]") ?? document.body;
    const links = within(list as HTMLElement).getAllByRole("link");
    expect(links).toHaveLength(6);                                  // berjalan dulu, lalu yang menunggu
    expect(links[0]).toHaveAttribute("href", "/work-plans/a");
    expect(screen.queryByText("SK h")).toBeNull();                  // selesai/batal tidak aktif
    expect(screen.queryByText("SK i")).toBeNull();
  });

  it("karyawan lapangan tidak melihat kartu pemeriksaan absensi dan tidak memanggil /attendance", async () => {
    const calls = mockApi((c) => (c.url === "/work-plans" ? { data: [] } : undefined));
    renderRoute("/", { role: "field" });
    expect(await screen.findByText("Belum ada SK aktif.")).toBeInTheDocument();
    expect(screen.queryByText("Absensi perlu diperiksa")).toBeNull();
    expect(calls.some((c) => c.url === "/attendance")).toBe(false);
  });

  it("galat memuat SK: pesan galat, bukan 'Belum ada SK aktif'", async () => {
    mockApi(() => apiError(500, "INTERNAL_ERROR", "Terjadi kesalahan."));
    renderRoute("/", { role: "field" });
    expect(await screen.findByText("Daftar SK tidak dapat dimuat.")).toBeInTheDocument();
    expect(screen.queryByText("Belum ada SK aktif.")).toBeNull();
  });

  it("HR: dokumen mendekati kedaluwarsa (≤ 30 hari / lewat) tampil, yang aman tidak", async () => {
    const doc = (id: string, urgency: string, days: number) => ({
      id, employee_id: `emp-${id}`, full_name: `Karyawan ${id}`, doc_type: "SIM A",
      expiry_date: "2026-10-01", days_left: days, urgency,
    });
    const calls = mockApi((c) => {
      if (c.url === "/work-plans") return { data: [] };
      if (c.url === "/documents/expiring")
        return { data: { items: [doc("a", "KEDALUWARSA", -2), doc("b", "KURANG_DARI_7_HARI", 3), doc("c", "KURANG_DARI_30_HARI", 20), doc("d", "AMAN", 200)] } };
    });
    renderRoute("/", { role: "HR" });

    const card = (await screen.findByText("Dokumen mendekati kedaluwarsa", { selector: "[data-slot=card-title]" })).closest("[data-slot=card]") as HTMLElement;
    const statLink = screen.getByRole("link", { name: /Dokumen mendekati kedaluwarsa/ });
    expect(statLink).toHaveAttribute("href", "/directory");
    expect(await within(statLink).findByText("3")).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: /Karyawan a/ })).toHaveAttribute("href", "/directory/emp-a");
    expect(within(card).getByText("Kedaluwarsa")).toBeInTheDocument();
    expect(within(card).getByText("< 7 hari")).toBeInTheDocument();
    expect(within(card).queryByText("Karyawan d")).toBeNull();
    expect(calls.some((c) => c.url === "/documents/expiring")).toBe(true);
  });

  it("tanpa izin verifikasi dokumen: tidak memanggil /documents/expiring", async () => {
    const calls = mockApi((c) => (c.url === "/work-plans" ? { data: [] } : undefined));
    renderRoute("/", { role: "PM" });
    await screen.findByText("Belum ada SK aktif.");
    expect(calls.some((c) => c.url === "/documents/expiring")).toBe(false);
  });
});
