import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

const plan = {
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
  status: "IN_PROGRESS",
  revision: 0,
  row_version: 5,
  cancellation_reason: null,
  appeal_reason: null,
};
const week = (over: Record<string, unknown> = {}) => ({
  week: 1,
  name: "Minggu 1",
  starts_on: "2026-10-01",
  ends_on: "2026-10-07",
  status: "DRAFT",
  body: "",
  obstacle: "",
  review_note: null,
  days_approved: true,
  ...over,
});

const setup = (weeks: unknown[], extra?: (url: string, method: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "", c.method ?? "get");
    if (hit) return hit;
    if (c.url === "/work-plans/p1") return { data: plan };
    if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    if (c.url === "/work-plans/p1/weekly") return { data: weeks };
  });

describe("Laporan mingguan", () => {
  it("menunggu laporan harian disetujui", async () => {
    setup([week({ days_approved: false })]);
    renderRoute("/work-plans/p1", { role: "field" });
    expect(await screen.findByText(/harus disetujui PM sebelum laporan mingguan dapat dibuat/)).toBeInTheDocument();
  });

  it("ketua menyimpan lalu mengirim (PUT lalu POST submit)", async () => {
    const calls = setup([week()], (url, method) => {
      if (url === "/work-plans/p1/weekly/1" && method === "put") return { data: week({ body: "Kabel terpasang", obstacle: "Tidak ada" }) };
      if (url === "/work-plans/p1/weekly/1/submit") return { data: week({ status: "SUBMITTED" }) };
    });
    renderRoute("/work-plans/p1", { role: "field" });
    const panel = await screen.findByRole("article", { name: "Minggu 1" });
    fireEvent.click(within(panel).getByRole("button", { name: "Kirim laporan" }));
    expect(await within(panel).findByText("Laporan mingguan wajib diisi.")).toBeInTheDocument();
    fireEvent.change(within(panel).getByLabelText("Laporan Mingguan"), { target: { value: "Kabel terpasang" } });
    fireEvent.change(within(panel).getByLabelText("Ringkasan Kendala Mingguan (Wajib)"), { target: { value: "Tidak ada" } });
    fireEvent.click(within(panel).getByRole("button", { name: "Kirim laporan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/weekly/1/submit")).toBe(true));
    expect(calls.find((c) => c.method === "put")!.data).toEqual({ body: "Kabel terpasang", obstacle: "Tidak ada" });
  });

  it("PM mengembalikan dengan catatan wajib", async () => {
    const calls = setup([week({ status: "SUBMITTED", body: "Isi", obstacle: "Tidak ada" })], (url) =>
      url === "/work-plans/p1/weekly/1/review" ? { data: week({ status: "CHANGES_REQUESTED" }) } : undefined,
    );
    renderRoute("/work-plans/p1", { role: "PM" });
    const panel = await screen.findByRole("article", { name: "Minggu 1" });
    fireEvent.change(within(panel).getByLabelText("Keputusan"), { target: { value: "RETURN" } });
    fireEvent.click(within(panel).getByRole("button", { name: "Simpan keputusan" }));
    expect(await within(panel).findByText("Catatan revisi wajib diisi.")).toBeInTheDocument();
    fireEvent.change(within(panel).getByLabelText("Catatan (wajib jika dikembalikan)"), { target: { value: "Lengkapi foto" } });
    fireEvent.click(within(panel).getByRole("button", { name: "Simpan keputusan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/weekly/1/review")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/p1/weekly/1/review")!.data).toEqual({ decision: "RETURN", note: "Lengkapi foto" });
  });

  it("kosong", async () => {
    setup([]);
    renderRoute("/work-plans/p1", { role: "PM" });
    expect(await screen.findByText("Belum ada laporan mingguan.")).toBeInTheDocument();
  });
});
