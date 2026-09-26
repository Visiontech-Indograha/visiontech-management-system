import { act, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

/**
 * R-19: PM membaca laporan akhir sebelum menyetujui (dulu tidak bisa dibaca), tim SK tampil
 * (dulu hanya ketua), dan mode presentasi laporan untuk SK selesai (M5).
 */

const plan = (status: string) => ({
  id: "p1", title: "Instalasi CCTV", unit_id: "u1", site_id: null, location_text: "Cikarang", description: null,
  period_start: "2026-10-01", period_end: "2026-10-20", pm_employee_id: "e-pm", leader_employee_id: "e-lead",
  number: "SK-202610-1a2b3c4d", status, revision: 0, row_version: 7, cancellation_reason: null, appeal_reason: null,
});
const team = [
  { employee_id: "e-lead", full_name: "Aris Setyawan", position: "Teknisi", role_in_plan: "LEADER", valid_from: "2026-10-01" },
  { employee_id: "e-mem", full_name: "Asrul Mulya", position: "Teknisi", role_in_plan: "MEMBER", valid_from: "2026-10-01" },
];
const report = (over: Record<string, unknown> = {}) => ({
  status: "SUBMITTED",
  body: "28 kamera terpasang dan diuji.",
  obstacle: "Hujan dua hari.",
  evidence_file_ids: [],
  submitted_at: "2026-10-20T09:00:00Z",
  submitted_by_name: "Aris Setyawan",
  review_note: null,
  reviewed_at: null,
  reviewed_by_name: null,
  ...over,
});

const setup = (status: string, finalReport: unknown, incidents: unknown[] = []) =>
  mockApi((c) => {
    if (c.url === "/work-plans/p1") return { data: plan(status) };
    if (c.url === "/work-plans/p1/members") return { data: team };
    if (c.url === "/work-plans/p1/completion") return { data: finalReport };
    if (c.url === "/hse/incidents") return { data: incidents };
    if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    if (c.url === "/work-plans/p1/weekly" || c.url === "/work-plans/p1/days") return { data: [] };
  });

describe("detail SK: tim & laporan akhir", () => {
  it("PM membaca laporan akhir saat menunggu persetujuan, dan melihat seluruh tim", async () => {
    setup("COMPLETION_REVIEW", report());
    renderRoute("/work-plans/p1", { role: "PM" });

    const panel = await screen.findByRole("region", { name: "Laporan akhir" });
    expect(within(panel).getByText("28 kamera terpasang dan diuji.")).toBeInTheDocument();
    expect(within(panel).getByText("Hujan dua hari.")).toBeInTheDocument();
    expect(within(panel).getByText(/Diajukan Aris Setyawan/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Setujui penyelesaian" })).toBeInTheDocument();

    const tim = screen.getByRole("region", { name: "Tim" });
    await waitFor(() => expect(within(tim).getByText("Asrul Mulya")).toBeInTheDocument());
    expect(within(tim).getByText("Ketua")).toBeInTheDocument();
    expect(within(tim).getByText("Anggota")).toBeInTheDocument();
  });

  it("tanpa laporan akhir: panel tidak tampil", async () => {
    setup("IN_PROGRESS", null);
    renderRoute("/work-plans/p1", { role: "field" });
    await screen.findByRole("region", { name: "Tim" });
    expect(screen.queryByRole("region", { name: "Laporan akhir" })).toBeNull();
  });

  it("dikembalikan: catatan PM terlihat oleh tim", async () => {
    setup("IN_PROGRESS", report({ status: "CHANGES_REQUESTED", review_note: "Lampirkan BAST.", reviewed_by_name: "Ade Candra" }));
    renderRoute("/work-plans/p1", { role: "field" });
    const panel = await screen.findByRole("region", { name: "Laporan akhir" });
    expect(within(panel).getByText("Lampirkan BAST.")).toBeInTheDocument();
    expect(within(panel).getByText(/Catatan Ade Candra/)).toBeInTheDocument();
  });
});

describe("mode presentasi laporan (M5)", () => {
  it("SK selesai: tombol di detail membuka slide sampul → tim → hasil → insiden → lampiran → pengesahan", async () => {
    setup(
      "COMPLETED",
      report({ status: "APPROVED", review_note: "Rapi", reviewed_at: "2026-10-21T02:00:00Z", reviewed_by_name: "Ade Candra" }),
      [{ id: "i1", work_plan_id: "p1", reported_by: "e-mem", occurred_on: "2026-10-05", category: "K3_HAMPIR", severity: "RENDAH",
         description: "Tangga licin.", status: "RESOLVED", resolved_by: null, resolved_at: null, resolution_note: null,
         created_at: "2026-10-05T03:00:00Z", evidence_file_ids: [] }],
    );
    const { router } = renderRoute("/work-plans/p1", { role: "PM" });
    const link = await screen.findByRole("link", { name: "Mode presentasi laporan" });
    expect(link).toHaveAttribute("href", "/work-plans/p1/presentation");

    await act(() => router.navigate("/work-plans/p1/presentation"));
    expect(await screen.findByRole("button", { name: "Simpan PDF" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Instalasi CCTV" })).toBeInTheDocument();
    const titles = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(titles).toEqual(["Tim", "Hasil pelaksanaan", "Insiden / K3", "Lampiran pendukung", "Pengesahan"]);
    expect(screen.getByText("SK-202610-1a2b3c4d")).toBeInTheDocument();
    expect(screen.getByText("Asrul Mulya")).toBeInTheDocument();
    expect(screen.getByText(/Tangga licin/)).toBeInTheDocument();
    expect(screen.getByText("Ade Candra")).toBeInTheDocument();
    expect(screen.getByText("6 / 6")).toBeInTheDocument();
  });

  it("SK belum selesai tidak bisa dipresentasikan dan tombolnya tidak tampil", async () => {
    setup("IN_PROGRESS", null);
    const { router } = renderRoute("/work-plans/p1", { role: "PM" });
    await screen.findByRole("region", { name: "Tim" });
    expect(screen.queryByRole("link", { name: "Mode presentasi laporan" })).toBeNull();

    await act(() => router.navigate("/work-plans/p1/presentation"));
    expect(await screen.findByText("Hanya pekerjaan yang sudah selesai yang dapat dipresentasikan.")).toBeInTheDocument();
  });
});
