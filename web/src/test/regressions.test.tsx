import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

/** Regresi wajib dok 07 §3 yang belum punya uji: R1 (dialog bawaan) dan R5 (teks laporan hilang). */

const plan = {
  id: "p1", title: "Instalasi CCTV", unit_id: "u1", site_id: null, location_text: "Cikarang", description: null,
  period_start: "2026-01-01", period_end: "2099-12-31", pm_employee_id: "e-pm", leader_employee_id: "e-lead",
  number: "Rencana Kerja/001", status: "IN_PROGRESS", revision: 0, row_version: 5, cancellation_reason: null, appeal_reason: null,
};
const day = {
  id: "d1", work_date: "2026-01-05", title: "Tarik kabel", sort_order: 1,
  tasks: [{ id: "t1", title: "Tarik kabel lantai 1", sort_order: 1, is_done: false, done_at: null }],
  report: null,
};

const api = (extra?: (url: string, method: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "", c.method ?? "get");
    if (hit) return hit;
    if (c.url === "/work-plans") return { data: [plan] };
    if (c.url === "/work-plans/p1") return { data: plan };
    if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    if (c.url === "/work-plans/p1/weekly") return { data: [] };
    if (c.url === "/work-plans/p1/days") return { data: [day] };
  });

const panel = () => screen.findByRole("article", { name: /Tarik kabel — / });

describe("R5 · teks laporan tidak hilang saat berpindah layar", () => {
  it("draf laporan harian dipulihkan setelah pindah ke daftar rencana kerja lalu kembali", async () => {
    api();
    const { router } = renderRoute("/work-plans/p1", { role: "field" });
    fireEvent.change(within(await panel()).getByLabelText("Laporan Harian"), {
      target: { value: "Kabel lantai 1 ditarik 40 meter" },
    });
    fireEvent.change(within(await panel()).getByLabelText("Kendala (Wajib)"), { target: { value: "Hujan sore" } });

    await act(() => router.navigate("/work-plans"));
    await screen.findByRole("heading", { level: 1 });
    await act(() => router.navigate("/work-plans/p1"));

    const p = await panel();
    expect(within(p).getByLabelText("Laporan Harian")).toHaveValue("Kabel lantai 1 ditarik 40 meter");
    expect(within(p).getByLabelText("Kendala (Wajib)")).toHaveValue("Hujan sore");
  });

  it("draf dibuang setelah laporan tersimpan ke server", async () => {
    let saved: unknown = null;
    api((url, method) => {
      if (url === "/work-plans/p1/days/d1" && method === "put") {
        saved = { status: "DRAFT", body: "Kabel lantai 1 selesai", obstacle: "Tidak ada", review_note: null,
                  submitted_at: null, reviewed_at: null, evidence_file_ids: [] };
        return { data: saved };
      }
    });
    const { router } = renderRoute("/work-plans/p1", { role: "field" });
    const p = await panel();
    fireEvent.change(within(p).getByLabelText("Laporan Harian"), { target: { value: "Kabel lantai 1 selesai" } });
    fireEvent.change(within(p).getByLabelText("Kendala (Wajib)"), { target: { value: "Tidak ada" } });
    fireEvent.click(within(p).getByRole("button", { name: "Simpan draft" }));
    await waitFor(() => expect(saved).not.toBeNull());

    const { useDrafts } = await import("@/lib/drafts");
    await waitFor(() => expect(useDrafts.getState().drafts["daily:d1"]).toBeUndefined());
    await act(() => router.navigate("/work-plans"));
  });
});

describe("R1 · tidak ada dialog bawaan peramban", () => {
  // Seluruh kode sumber web (bukan uji) sebagai teks mentah — dikumpulkan Vite saat uji dijalankan.
  const sources = import.meta.glob(["/src/**/*.{ts,tsx}", "!/src/test/**", "!/src/**/*.test.{ts,tsx}"], {
    query: "?raw",
    import: "default",
    eager: true,
  }) as Record<string, string>;

  it("kode web tidak memanggil alert/confirm/prompt (membekukan halaman & otomasi)", () => {
    expect(Object.keys(sources).length).toBeGreaterThan(50);
    const offenders = Object.entries(sources)
      .filter(([, text]) => /(^|[^\w.])(window\.)?(alert|confirm|prompt)\s*\(/m.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });
});
