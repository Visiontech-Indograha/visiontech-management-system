import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "@/test/utils";

const borrower = { borrower_id: "b1", office_id: "o1", office_name: "Kantor Utama", nama: "Budi Sewa", instansi: "PT Maju", kontak: "0812", has_open_loan: true, create_at: "2026-11-01T00:00:00Z" };
const tool = { tool_id: "t1", office_id: "o1", office_name: "Kantor Utama", division_id: null, division_name: null, ownership_type: "SHARED_TOOL", category: "BOR", name: "Bor Bosch", tool_code: "TL-1", status: "ready" };
const extLoan = {
  assignment_id: "l9", asset_type: "TOOL", asset_id: "t2", asset_name: "Genset", asset_code: "TL-2", employee_id: null, employee_name: "Budi Sewa",
  external_borrower_id: "b1", borrower_name: "Budi Sewa", borrower_instansi: "PT Maju", due_date: "2020-01-01", daily_plan_id: null, work_date: null,
  assignment_status: "loaned", loaned_at: "2026-10-01T02:00:00Z", returned_at: null,
};

const setup = (extra?: Parameters<typeof mockApi>[0]) =>
  mockApi((c) => {
    const hit = extra?.(c);
    if (hit) return hit;
    const url = c.url ?? "";
    if (url === "/assets/external-borrowers") return { data: [borrower], headers: { "x-total-count": "1" } };
    if (url === "/assets/tools") return { data: [tool] };
    if (url === "/assets/vehicles") return { data: [] };
    if (url === "/assets/loans") return { data: [extLoan] };
    if (url === "/offices") return { data: [{ id: "o1", name: "Kantor Utama" }] };
    if (url === "/teams" || url === "/daily-plans") return { data: [] };
    if (url === "/employees") return { data: { items: [], total: 0, page: 1, size: 25 } };
  });

describe("Penerima luar aset", () => {
  it("daftar peminjaman menampilkan penerima luar dan tanggal kembali", async () => {
    setup();
    renderRoute("/assets", { role: "ASSET" });
    fireEvent.click(await screen.findByRole("button", { name: /^Sedang dipinjam/ }));
    expect(await screen.findByText(/Budi Sewa \(PT Maju\)/)).toBeInTheDocument();
    expect(screen.getByText("Pihak luar")).toBeInTheDocument();
    expect(screen.getByText("Lewat tanggal kembali")).toBeInTheDocument();
  });

  it("kelola penerima: daftar tampil dan tambah baru mengirim data", async () => {
    const calls = setup((c) => (c.url === "/assets/external-borrowers" && c.method === "post" ? { status: 201, data: borrower } : undefined));
    renderRoute("/assets", { role: "ASSET" });
    fireEvent.click(await screen.findByRole("button", { name: "Penerima luar" }));
    const list = await screen.findByRole("dialog", { name: "Penerima dari luar perusahaan" });
    expect(await within(list).findByText("Budi Sewa")).toBeInTheDocument();
    fireEvent.click(within(list).getByRole("button", { name: "Tambah penerima" }));
    const form = await screen.findByRole("dialog", { name: "Tambah penerima" });
    await within(form).findByRole("option", { name: "Kantor Utama" });
    fireEvent.change(within(form).getByLabelText("Kantor"), { target: { value: "o1" } });
    fireEvent.change(within(form).getByLabelText("Nama penerima"), { target: { value: "Sari" } });
    fireEvent.click(within(form).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/assets/external-borrowers")).toBe(true));
    expect(calls.find((c) => c.method === "post" && c.url === "/assets/external-borrowers")!.data).toEqual({ office_id: "o1", nama: "Sari", instansi: null, kontak: null });
  });

  it("serah ke penerima luar mengirim external_borrower_id dan tanggal kembali", async () => {
    const calls = setup((c) => (c.url === "/assets/loans" && c.method === "post" ? { status: 201, data: extLoan } : undefined));
    renderRoute("/assets", { role: "ASSET" });
    fireEvent.click(await screen.findByRole("button", { name: /^Alat/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Serahkan ke pihak luar" }));
    const dialog = screen.getByRole("dialog", { name: "Serahkan Bor Bosch ke pihak luar" });
    await within(dialog).findByRole("option", { name: /Budi Sewa/ });
    fireEvent.change(within(dialog).getByLabelText("Penerima", { selector: "select" }), { target: { value: "b1" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal harus kembali (opsional)"), { target: { value: "2099-01-01" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Serahkan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/assets/loans")).toBe(true));
    expect(calls.find((c) => c.method === "post" && c.url === "/assets/loans")!.data).toMatchObject({
      asset_type: "TOOL", tool_id: "t1", external_borrower_id: "b1", due_date: "2099-01-01", bast_file_id: null,
    });
  });
});
