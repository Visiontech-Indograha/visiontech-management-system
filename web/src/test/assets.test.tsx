import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const vehicle = (over: Record<string, unknown> = {}) => ({
  vehicle_id: "v1",
  office_id: "o1",
  office_name: "Kantor Utama",
  division_id: "d1",
  division_name: "Divisi Sipil",
  vehicle_type: "Car",
  name: "Avanza Operasional",
  number_plate: "BK 1452 ZN",
  status: "ready",
  stnk_expired_at: "2031-01-01",
  kir_expired_at: null,
  ...over,
});
const tool = (over: Record<string, unknown> = {}) => ({
  tool_id: "t1",
  office_id: "o1",
  office_name: "Kantor Utama",
  division_id: null,
  division_name: null,
  ownership_type: "SHARED_TOOL",
  category: "BOR",
  name: "Bor Bosch",
  tool_code: "TL-BOR-001",
  status: "ready",
  ...over,
});
const loan = {
  assignment_id: "l1", asset_type: "TOOL", asset_id: "t2", asset_name: "Laptop", asset_code: "TL-LPT-001",
  employee_id: "e1", employee_name: "Doni", daily_plan_id: null, work_date: null, assignment_status: "loaned",
  loaned_at: "2026-10-01T02:00:00Z", returned_at: null,
};
const employees = { items: [{ employee_id: "e1", full_name: "Doni", employee_no: "VT-08", join_date: "2024-01-01", offboarding_status: "active" }], total: 1, page: 1, size: 25 };

const setup = (extra?: (url: string, method: string) => { status?: number; data?: unknown } | undefined) =>
  mockApi((c) => {
    const hit = extra?.(c.url ?? "", c.method ?? "get");
    if (hit) return hit;
    if (c.url === "/assets/vehicles") return { data: [vehicle(), vehicle({ vehicle_id: "v2", name: "L300", vehicle_type: "Truck", number_plate: "BK 8821 XA" })] };
    if (c.url === "/assets/tools") return { data: [tool()] };
    if (c.url === "/assets/loans") return { data: [loan] };
    if (c.url === "/employees") return { data: employees };
  });

describe("Kendaraan dan alat (M4)", () => {
  it("kendaraan: status dan masa berkas; truk tanpa KIR ditandai; lapangan tanpa tombol kelola", async () => {
    setup();
    renderRoute("/assets", { role: "field" });
    expect(await screen.findByText("Avanza Operasional")).toBeInTheDocument();
    expect(screen.getAllByText("Siap").length).toBeGreaterThan(0);
    expect(screen.getByText("KIR belum ada")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Serahkan" })).toBeNull();
  });

  it("galat memuat menampilkan Coba lagi", async () => {
    mockApi(() => apiError(500, "INTERNAL_ERROR", "x"));
    renderRoute("/assets", { role: "ASSET" });
    expect((await screen.findAllByRole("button", { name: "Coba lagi" })).length).toBeGreaterThan(0);
  });

  it("pengelola menyerahkan alat ke karyawan", async () => {
    const calls = setup((url, method) => (url === "/assets/loans" && method === "post" ? { status: 201, data: loan } : undefined));
    renderRoute("/assets", { role: "ASSET" });
    fireEvent.click(await screen.findByRole("button", { name: /^Alat/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Serahkan" }));
    const dialog = screen.getByRole("dialog", { name: "Serahkan Bor Bosch" });
    await within(dialog).findByRole("option", { name: /Doni/ });
    fireEvent.change(within(dialog).getByLabelText("Karyawan penerima"), { target: { value: "e1" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Serahkan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/assets/loans")).toBe(true));
    expect(calls.find((c) => c.method === "post" && c.url === "/assets/loans")!.data).toEqual({
      asset_type: "TOOL", tool_id: "t1", employee_id: "e1", handover_file_id: null,
    });
  });

  it("pengelola menerima pengembalian dengan kondisi rusak", async () => {
    const calls = setup((url) => (url === "/assets/loans/l1/return" ? { data: { ...loan, returned_at: "x" } } : undefined));
    renderRoute("/assets", { role: "ASSET" });
    fireEvent.click(await screen.findByRole("button", { name: /^Sedang dipinjam/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Terima kembali" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Kondisi saat dikembalikan"), { target: { value: "damaged" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Terima pengembalian" }));
    await waitFor(() => expect(calls.find((c) => c.url === "/assets/loans/l1/return")?.data).toEqual({ condition: "damaged" }));
  });
});
