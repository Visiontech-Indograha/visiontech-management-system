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
});
