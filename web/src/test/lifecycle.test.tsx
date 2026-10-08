import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const page = (items: unknown[]) => ({ items, total: items.length, page: 1, size: 25 });
const employee = (over: Record<string, unknown> = {}) => ({
  id: "e1",
  employee_no: "VT-001",
  full_name: "Test User",
  position: "Teknisi",
  join_date: "2024-01-01",
  email: null,
  phone: null,
  is_active: false,
  offboarded_at: "2026-09-01T00:00:00Z",
  offboarding_reason: "Resign",
  ...over,
});
const plan = (status: string) => ({
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
  number: null,
  status,
  revision: 0,
  row_version: 1,
  cancellation_reason: null,
  appeal_reason: null,
});
const att = (id: string, name: string) => ({ file_id: id, file_name: name, mime_type: "application/pdf", byte_size: 2048, sort_order: 0 });

const openDetail = async (
  emp: ReturnType<typeof employee>,
  extra?: (url: string, method: string) => { status?: number; data?: unknown } | undefined,
) => {
  const calls = mockApi((c) => {
    const hit = extra?.(c.url ?? "", c.method ?? "get");
    if (hit) return hit;
    if (c.url === "/employees") return { data: page([emp]) };
    if (c.url === "/employees/e1/documents") return { data: { items: [], total: 0 } };
  });
  renderRoute("/directory", { role: "HR" });
  fireEvent.click(await screen.findByRole("link", { name: "Test User" }));
  return calls;
};

describe("Hapus & pulihkan karyawan (HR)", () => {
  it("karyawan aktif tidak menampilkan tombol hapus", async () => {
    await openDetail(employee({ is_active: true, offboarded_at: null }));
    expect(await screen.findByText("Teknisi")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hapus karyawan" })).toBeNull();
  });

  it("hapus lewat konfirmasi lalu pulihkan", async () => {
    const calls = await openDetail(employee(), (url) => {
      if (url === "/employees/e1/archive") return { data: { id: "e1", message: "ok" } };
      if (url === "/employees/e1/restore") return { data: { id: "e1", is_active: false, message: "ok" } };
    });
    fireEvent.click(await screen.findByRole("button", { name: "Hapus karyawan" }));
    fireEvent.click(await screen.findByRole("button", { name: "Ya, hapus" }));
    expect(await screen.findByText(/sudah dihapus dan tidak tampil di Direktori/)).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/employees/e1/archive" && c.method === "post")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Pulihkan karyawan" }));
    expect(await screen.findByRole("button", { name: "Hapus karyawan" })).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/employees/e1/restore" && c.method === "post")).toBe(true);
  });

  it("penolakan API ditampilkan", async () => {
    await openDetail(employee(), (url) =>
      url === "/employees/e1/archive" ? apiError(409, "INVALID_STATE", "Akhiri masa kerja karyawan ini terlebih dahulu.") : undefined,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Hapus karyawan" }));
    fireEvent.click(await screen.findByRole("button", { name: "Ya, hapus" }));
    expect(await screen.findByText("Akhiri masa kerja karyawan ini terlebih dahulu.")).toBeInTheDocument();
  });
});

const setupPlan = (
  status: string,
  list: unknown[],
  extra?: (url: string, method: string) => { status?: number; data?: unknown } | undefined,
) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "", c.method ?? "get");
    if (hit) return hit;
    if (c.url === "/work-plans/p1") return { data: plan(status) };
    if (c.url === "/employees") return { data: page([]) };
    if (c.url === "/work-plans/p1/attachments") return { data: list };
    if (c.url?.startsWith("/files/")) return { data: { url: "http://x/f", mime_type: "application/pdf" } };
  });

describe("Lampiran SK", () => {
  it("PM menghapus lampiran draf → PUT daftar tersisa", async () => {
    const calls = setupPlan("DRAFT", [att("f1", "RAB.pdf"), att("f2", "Denah.pdf")], (url, method) =>
      url === "/work-plans/p1/attachments" && method === "put" ? { data: [att("f2", "Denah.pdf")] } : undefined,
    );
    renderRoute("/work-plans/p1", { role: "PM" });
    const section = await screen.findByRole("region", { name: "Lampiran SK" });
    fireEvent.click(await within(section).findByRole("button", { name: "Hapus RAB.pdf" }));
    await waitFor(() => expect(within(section).queryByText("RAB.pdf")).toBeNull());
    expect(calls.find((c) => c.method === "put")!.data).toEqual({ file_ids: ["f2"] });
  });

  it("PM menambah lampiran: unggah lalu PUT daftar lengkap", async () => {
    const calls = setupPlan("DRAFT", [att("f1", "RAB.pdf")], (url, method) => {
      if (url === "/files/upload") return { data: { file_id: "f9", message: "ok" } };
      if (url === "/work-plans/p1/attachments" && method === "put") return { data: [att("f1", "RAB.pdf"), att("f9", "Baru.pdf")] };
    });
    renderRoute("/work-plans/p1", { role: "PM" });
    const section = await screen.findByRole("region", { name: "Lampiran SK" });
    const input = await within(section).findByLabelText("Tambah lampiran (Foto/PDF)");
    fireEvent.change(input, { target: { files: [new File(["x"], "Baru.pdf", { type: "application/pdf" })] } });
    expect(await within(section).findByText("Baru.pdf")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "put")!.data).toEqual({ file_ids: ["f1", "f9"] });
  });

  it("SK terbit: lampiran hanya dibaca", async () => {
    setupPlan("PUBLISHED", [att("f1", "RAB.pdf")]);
    renderRoute("/work-plans/p1", { role: "PM" });
    const section = await screen.findByRole("region", { name: "Lampiran SK" });
    expect(await within(section).findByText("RAB.pdf")).toBeInTheDocument();
    expect(within(section).queryByRole("button", { name: /Hapus/ })).toBeNull();
    expect(within(section).queryByLabelText("Tambah lampiran (Foto/PDF)")).toBeNull();
  });
});
