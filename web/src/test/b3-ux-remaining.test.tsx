import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { ClientList } from "@/components/organisms/clients/ClientList";
import { LeaveList } from "@/components/organisms/leaves/LeaveList";
import { WorkTypeMaterialsDialog } from "@/components/organisms/work-types/WorkTypeMaterialsDialog";
import type { Client } from "@/services/clientService";
import type { LeaveRequest } from "@/services/leaveService";
import type { WorkType } from "@/services/workTypeService";
import { mockApi } from "./utils";

const noop = () => {};
const query = <T,>(data: T): UseQueryResult<T> =>
  ({ data, isPending: false, isError: false, refetch: noop }) as unknown as UseQueryResult<T>;
const withClient = (ui: React.ReactElement) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

describe("daftar klien: empty state bercabang (W14)", () => {
  const clientProps = {
    canManage: true, onAdd: noop, onEdit: noop, onDeactivate: noop, onSearchChange: noop,
  };

  it("pencarian tanpa hasil memakai 'Klien tidak ditemukan', bukan 'Belum ada klien terdaftar'", () => {
    render(<ClientList {...clientProps} clients={query<Client[]>([])} search="xyz" />);
    expect(screen.getByText("Klien tidak ditemukan")).toBeTruthy();
    expect(screen.queryByText("Belum ada klien terdaftar")).toBeNull();
  });

  it("tanpa pencarian dan tanpa data tetap 'Belum ada klien terdaftar' dengan ajakan tambah", () => {
    render(<ClientList {...clientProps} clients={query<Client[]>([])} search="" />);
    expect(screen.getByText("Belum ada klien terdaftar")).toBeTruthy();
    expect(screen.getByRole("button", { name: /tambah/i })).toBeTruthy();
  });
});

describe("label status cuti sesuai pemberi persetujuan (W4)", () => {
  const leave = (over: Partial<LeaveRequest>) =>
    ({
      leave_id: "l1", employee_id: "e1", employee_name: "Budi", leave_type: "ANNUAL",
      start_date: "2026-10-30", end_date: "2026-10-30", total_days: 1, reason: "Keluarga",
      status: "APPROVED_BY_HR", create_at: "2026-10-28T00:00:00Z", reviewed_by_name: "Sari OM", ...over,
    }) as LeaveRequest;

  const renderList = (rows: LeaveRequest[]) =>
    withClient(
      <LeaveList
        leaves={query({ items: rows, total: rows.length, page: 1, size: 10 })}
        statusFilter="" onStatusFilterChange={noop} q="" onQChange={noop} page={1} onPageChange={noop}
        filtersActive={false} onResetFilters={noop} canReview={false} canFinalReview={false}
        onApply={noop} onReview={noop}
      />,
    );

  it("status final tidak menyebut 'HR' bila yang menyetujui OM", () => {
    renderList([leave({})]);
    expect(screen.queryByText("Disetujui HR")).toBeNull();
    expect(screen.getByText(/Disetujui · Sari OM/)).toBeTruthy();
  });
});

describe("material standar jenis pekerjaan (W11)", () => {
  const workType = { id: "wt-1", name: "Penyambungan FO", division_id: "d1", division_name: "FO", is_active: true, photos: [] } as unknown as WorkType;

  function renderDialog() {
    mockApi((c) => {
      if (c.url === "/work-types/wt-1/materials" && c.method === "get") return { data: [] };
    });
    return withClient(<WorkTypeMaterialsDialog workType={workType} onClose={noop} />);
  }

  it("satuan kosong saat form dibuka (placeholder, bukan nilai 'Unit')", async () => {
    renderDialog();
    fireEvent.click(await screen.findByRole("button", { name: /Tambah Material/ }));
    const satuan = screen.getByLabelText("Satuan") as HTMLInputElement;
    expect(satuan.value).toBe("");
    expect(satuan.placeholder).toContain("Meter");
  });

  it("nama kosong dan kebutuhan 0 menampilkan galat di kolomnya dan tidak mengirim", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-types/wt-1/materials" && c.method === "get") return { data: [] };
    });
    renderDialog();
    fireEvent.click(await screen.findByRole("button", { name: /Tambah Material/ }));
    fireEvent.change(screen.getByLabelText("Satuan"), { target: { value: "Meter" } });
    fireEvent.change(screen.getByLabelText("Kebutuhan Default"), { target: { value: "0" } });
    fireEvent.click(screen.getByRole("button", { name: "Simpan Template" }));
    expect(await screen.findByText("Nama material wajib diisi.")).toBeTruthy();
    expect(await screen.findByText("Kebutuhan default harus lebih dari 0.")).toBeTruthy();
    expect(calls.some((c) => c.method === "post")).toBe(false);
  });

  it("nilai satuan yang diketik tidak digabung dengan nilai bawaan", async () => {
    renderDialog();
    fireEvent.click(await screen.findByRole("button", { name: /Tambah Material/ }));
    const satuan = screen.getByLabelText("Satuan") as HTMLInputElement;
    fireEvent.change(satuan, { target: { value: "Meter" } });
    await waitFor(() => expect(satuan.value).toBe("Meter"));
  });
});
