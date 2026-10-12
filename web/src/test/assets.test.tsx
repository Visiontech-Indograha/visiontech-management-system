import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const asset = (over: Record<string, unknown> = {}) => ({
  id: "a1",
  kind: "VEHICLE",
  vehicle_type: "Pick-up",
  code: "KDR-01",
  name: "L300 Putih",
  condition: "Baik",
  status: "AVAILABLE",
  ...over,
});
const plan = { id: "p1", title: "Instalasi CCTV", number: "Rencana Kerja/001", status: "IN_PROGRESS" };
const employees = { items: [{ id: "e1", full_name: "Budi Supir", position: "Driver", employee_no: "1", join_date: "2024-01-01", is_active: true }], total: 1, page: 1, size: 100 };

const setup = (assets: unknown[], extra?: (url: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "");
    if (hit) return hit;
    if (c.url === "/assets") return { data: assets };
    if (c.url === "/work-plans") return { data: [plan, { ...plan, id: "p2", title: "Draf", status: "DRAFT" }] };
    if (c.url === "/employees") return { data: employees };
  });

describe("Kendaraan & alat", () => {
  it("daftar, kosong, galat", async () => {
    setup([asset()]);
    const first = renderRoute("/assets", { role: "field" });
    expect(await screen.findByText("L300 Putih")).toBeInTheDocument();
    expect(screen.getByText("Tersedia")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Alokasikan" })).toBeNull();
    first.unmount();
    mockApi(() => apiError(500, "INTERNAL_ERROR", "x"));
    renderRoute("/assets", { role: "ASSET" });
    expect(await screen.findByRole("button", { name: "Coba lagi" })).toBeInTheDocument();
  });

  it("alokasi kendaraan wajib pengemudi; hanya rencana kerja aktif ditawarkan", async () => {
    const calls = setup([asset()], (url) =>
      url === "/assets/a1/reserve"
        ? { data: { id: "al1", asset_id: "a1", work_plan_id: "p1", driver_employee_id: "e1", allocated_by: "u", allocated_at: "2026-10-01T00:00:00Z", released_at: null } }
        : undefined,
    );
    renderRoute("/assets", { role: "ASSET" });
    fireEvent.click(await screen.findByRole("button", { name: "Alokasikan" }));
    const dialog = screen.getByRole("dialog", { name: "Alokasikan L300 Putih" });
    await within(dialog).findByRole("option", { name: "Rencana Kerja/001 · Instalasi CCTV" });
    expect(within(dialog).queryByRole("option", { name: /Draf/ })).toBeNull();
    fireEvent.change(within(dialog).getByLabelText("Work plan"), { target: { value: "p1" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Alokasikan" }));
    expect(await within(dialog).findByText("Pilih pengemudi untuk aset kendaraan.")).toBeInTheDocument();
    await within(dialog).findByRole("option", { name: "Budi Supir" });
    fireEvent.change(within(dialog).getByLabelText("Pengemudi"), { target: { value: "e1" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Alokasikan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/assets/a1/reserve")).toBe(true));
    expect(calls.find((c) => c.url === "/assets/a1/reserve")!.data).toEqual({ work_plan_id: "p1", driver_employee_id: "e1" });
  });

  it("pengemudi mengajukan banding kelayakan dengan alasan", async () => {
    const calls = setup([asset({ status: "RESERVED" })], (url) =>
      url === "/assets/a1/check" ? { data: { asset_id: "a1", status: "AVAILABLE" } } : undefined,
    );
    renderRoute("/assets", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Periksa Kendaraan" }));
    const dialog = screen.getByRole("dialog", { name: "Periksa Kendaraan" });
    fireEvent.change(within(dialog).getByLabelText("Hasil pemeriksaan"), { target: { value: "APPEAL" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan hasil" }));
    expect(await within(dialog).findByText("Alasan banding kelayakan wajib diisi.")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Alasan (wajib jika banding)"), { target: { value: "Rem blong" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan hasil" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/assets/a1/check")).toBe(true));
    expect(calls.find((c) => c.url === "/assets/a1/check")!.data).toEqual({ decision: "APPEAL", reason: "Rem blong" });
  });

  it("petugas aset menambah alat dengan vehicle_type null", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/assets" && c.method === "post") return { status: 201, data: asset({ id: "a2", kind: "TOOL" }) };
      if (c.url === "/assets") return { data: [] };
    });
    renderRoute("/assets", { role: "ASSET" });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah aset" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah aset" });
    fireEvent.change(within(dialog).getByLabelText("Jenis aset"), { target: { value: "TOOL" } });
    fireEvent.change(within(dialog).getByLabelText("Kode aset"), { target: { value: "ALT-1" } });
    fireEvent.change(within(dialog).getByLabelText("Nama aset"), { target: { value: "Bor" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(calls.find((c) => c.method === "post")!.data).toEqual({ kind: "TOOL", vehicle_type: null, code: "ALT-1", name: "Bor", condition: "Baik" });
  });

  it("melepas reservasi mengirim work_plan_id", async () => {
    const calls = setup([asset({ status: "RESERVED" })], (url) =>
      url === "/assets/a1/release" ? { data: { asset_id: "a1", status: "AVAILABLE" } } : undefined,
    );
    renderRoute("/assets", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Lepas reservasi" }));
    const dialog = screen.getByRole("dialog", { name: "Lepas reservasi L300 Putih" });
    await within(dialog).findByRole("option", { name: "Rencana Kerja/001 · Instalasi CCTV" });
    fireEvent.change(within(dialog).getByLabelText("Work plan"), { target: { value: "p1" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Lepas reservasi" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/assets/a1/release")).toBe(true));
    expect(calls.find((c) => c.url === "/assets/a1/release")!.data).toEqual({ work_plan_id: "p1" });
  });
});
