import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const plan = {
  id: "p1",
  title: "Instalasi CCTV",
  unit_id: "u1",
  site_id: null,
  location_text: "Cikarang",
  description: null,
  period_start: "2026-01-01",
  period_end: "2099-12-31",
  pm_employee_id: "e-pm",
  leader_employee_id: "e-lead",
  number: "Rencana Kerja/001",
  status: "IN_PROGRESS",
  revision: 0,
  row_version: 5,
  cancellation_reason: null,
  appeal_reason: null,
};
const report = (over: Record<string, unknown> = {}) => ({
  status: "DRAFT",
  body: "",
  obstacle: "",
  review_note: null,
  submitted_at: null,
  reviewed_at: null,
  evidence_file_ids: [],
  ...over,
});
const day = (over: Record<string, unknown> = {}) => ({
  id: "d1",
  work_date: "2026-01-05",
  title: "Tarik kabel",
  sort_order: 1,
  tasks: [
    {
      id: "t2",
      title: "Pasang kamera",
      sort_order: 2,
      is_done: false,
      done_at: null,
    },
    {
      id: "t1",
      title: "Tarik kabel lantai 1",
      sort_order: 1,
      is_done: false,
      done_at: null,
    },
  ],
  report: null,
  ...over,
});

const setup = (days: unknown[], extra?: (url: string, method: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "", c.method ?? "get");
    if (hit) return hit;
    if (c.url === "/work-plans/p1") return { data: plan };
    if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    if (c.url === "/work-plans/p1/weekly") return { data: [] };
    if (c.url === "/work-plans/p1/days") return { data: days };
  });

const panel = () => screen.findByRole("article", { name: /Tarik kabel — / });

describe("Laporan harian", () => {
  it("menampilkan tugas terurut dan mencentang lewat toggle", async () => {
    const calls = setup([day()], (url) =>
      url === "/work-plans/p1/days/d1/tasks/t1/toggle" ? { data: { id: "t1", is_done: true } } : undefined,
    );
    renderRoute("/work-plans/p1", { role: "field" });
    const p = await panel();
    const boxes = within(p).getAllByRole("checkbox");
    expect(boxes.map((b) => b.closest("label")!.textContent)).toEqual(["Tarik kabel lantai 1", "Pasang kamera"]);
    fireEvent.click(boxes[0]);
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/days/d1/tasks/t1/toggle" && c.method === "post")).toBe(true));
  });

  it("toggle ditolak API → pesan galat tampil", async () => {
    setup([day()], (url) =>
      url.endsWith("/toggle") ? apiError(409, "INVALID_STATE", "Daftar tugas tidak dapat diubah setelah laporan diserahkan.") : undefined,
    );
    renderRoute("/work-plans/p1", { role: "field" });
    fireEvent.click(within(await panel()).getAllByRole("checkbox")[0]);
    expect(await screen.findByText("Daftar tugas tidak dapat diubah setelah laporan diserahkan.")).toBeInTheDocument();
  });

  it("ketua menyimpan lalu mengirim (PUT lalu POST submit)", async () => {
    const calls = setup([day()], (url, method) => {
      if (url === "/work-plans/p1/days/d1" && method === "put") return { data: {} };
      if (url === "/work-plans/p1/days/d1/submit") return { data: {} };
    });
    renderRoute("/work-plans/p1", { role: "field" });
    const p = await panel();
    fireEvent.click(within(p).getByRole("button", { name: "Kirim laporan" }));
    expect(await within(p).findByText("Laporan harian minimal 10 karakter.")).toBeInTheDocument();
    fireEvent.change(within(p).getByLabelText("Laporan Harian"), {
      target: { value: "Kabel lantai 1 selesai" },
    });
    fireEvent.change(within(p).getByLabelText("Kendala (Wajib)"), {
      target: { value: "Tidak ada" },
    });
    fireEvent.click(within(p).getByRole("button", { name: "Kirim laporan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/days/d1/submit")).toBe(true));
    expect(calls.find((c) => c.method === "put")!.data).toEqual({
      body: "Kabel lantai 1 selesai",
      obstacle: "Tidak ada",
      evidence_file_ids: [],
    });
  });

  it("laporan terkirim: checklist terkunci, PM memutuskan dengan catatan wajib saat dikembalikan", async () => {
    const calls = setup(
      [
        day({
          report: report({
            status: "SUBMITTED",
            body: "Kabel selesai",
            obstacle: "Tidak ada",
          }),
        }),
      ],
      (url) => (url === "/work-plans/p1/days/d1/review" ? { data: {} } : undefined),
    );
    renderRoute("/work-plans/p1", { role: "PM" });
    const p = await panel();
    expect(
      within(p)
        .getAllByRole("checkbox")
        .every((b) => (b as HTMLInputElement).disabled),
    ).toBe(true);
    expect(within(p).getByText("Kabel selesai")).toBeInTheDocument();
    fireEvent.change(within(p).getByLabelText("Keputusan"), {
      target: { value: "RETURN" },
    });
    fireEvent.click(within(p).getByRole("button", { name: "Simpan keputusan" }));
    expect(await within(p).findByText("Catatan revisi wajib diisi.")).toBeInTheDocument();
    fireEvent.change(within(p).getByLabelText("Catatan (wajib jika dikembalikan)"), { target: { value: "Tambah foto" } });
    fireEvent.click(within(p).getByRole("button", { name: "Simpan keputusan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/days/d1/review")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/p1/days/d1/review")!.data).toEqual({ decision: "RETURN", note: "Tambah foto" });
  });

  it("hari yang belum tiba tidak bisa diisi", async () => {
    setup([day({ work_date: "2099-01-01" })]);
    renderRoute("/work-plans/p1", { role: "field" });
    const p = await panel();
    expect(within(p).getByText(/Laporan dapat diisi mulai/)).toBeInTheDocument();
    expect(within(p).queryByRole("button", { name: "Kirim laporan" })).toBeNull();
    expect(
      within(p)
        .getAllByRole("checkbox")
        .every((b) => (b as HTMLInputElement).disabled),
    ).toBe(true);
  });
});
