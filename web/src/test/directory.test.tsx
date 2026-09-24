import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

const page = (items: unknown[]) => ({ items, total: items.length, page: 1, size: 25 });
const employee = (id = "e1") => ({
  id,
  username: "user",
  full_name: "Test User",
  role: "user",
  user_type: "DRIVER",
  is_active: true,
});
const doc = (overrides: Record<string, unknown> = {}) => ({
  id: "d1",
  employee_id: "e1",
  doc_type: "KTP",
  number_masked: "123***",
  expiry_date: "2025-01-01",
  status: "VALID",
  lifecycle: "ACTIVE",
  file_id: "f1",
  uploaded_by: "u1",
  created_at: "2024-01-01T00:00:00Z",
  ...overrides,
});

describe("halaman direktori utama", () => {
  it("menampilkan daftar", async () => {
    mockApi((c) => (c.url === "/employees" ? { data: page([employee()]) } : undefined));
    renderRoute("/directory", { role: "HR" });
    expect(await screen.findByText("Test User")).toBeInTheDocument();
  });

  it("filter dan status default 'Aktif' dikirim ke server", async () => {
    const calls = mockApi((c) => (c.url === "/employees" ? { data: page([]) } : undefined));
    renderRoute("/directory", { role: "HR" });
    await screen.findByText("Tidak ada karyawan yang cocok.");
    expect(calls[0]).toBeDefined();

    fireEvent.change(screen.getByLabelText("Cari nama atau username"), { target: { value: "test" } });
    await waitFor(() => expect(calls.length).toBeGreaterThan(1));

    fireEvent.change(screen.getByLabelText("Filter akun"), { target: { value: "inactive" } });
    await waitFor(() => expect(calls.length).toBeGreaterThan(2));
  });
});

describe("halaman detail karyawan (SA / HES)", () => {
  it("menampilkan profil", async () => {
    mockApi((c) => {
      if (c.url === "/employees/e1") return { data: employee() };
      if (c.url === "/employees/e1/documents") return { data: { items: [doc()], total: 1 } };
    });
    renderRoute("/directory/e1", { role: "HR" });
    expect(await screen.findByText("KTP")).toBeInTheDocument();
  });

  it("menambah berkas mengirim form ke upload lalu ke documents", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees/e1") return { data: employee() };
      if (c.url === "/employees/e1/documents" && c.method === "get") return { data: { items: [], total: 0 } };
      if (c.url === "/files/upload" && c.method === "post") return { data: { id: "f1", url: "x", mime_type: "image/jpeg" } };
      if (c.url === "/employees/e1/documents" && c.method === "post") return { status: 201, data: doc({ id: "d2" }) };
    });
    renderRoute("/directory/e1", { role: "HR" });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah berkas" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah berkas" });

    fireEvent.change(within(dialog).getByLabelText(/Jenis dokumen/), { target: { value: "KTP" } });
    fireEvent.change(within(dialog).getByLabelText(/Nomor dokumen/), { target: { value: "123" } });
    
    // Simulate file upload
    const file = new File(["dummy content"], "test.png", { type: "image/png" });
    const fileInput = within(dialog).getByLabelText(/File/);
    Object.defineProperty(fileInput, "files", { value: [file] });
    fireEvent.change(fileInput);

    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const posts = calls.filter((c) => c.method === "post");
    expect(posts[0].url).toBe("/files/upload");
    expect(posts[1].url).toBe("/employees/e1/documents");
    expect(posts[1].data).toMatchObject({ doc_type: "KTP", number: "123", file_id: "f1" });
  });

  it("ubah profil mengirim status kerja dan tanggal", async () => {
    const calls = mockApi((c) => {
        if (c.url === "/employees/e1" && c.method === "get") return { data: employee() };
        if (c.url === "/employees/e1/documents" && c.method === "get") return { data: { items: [], total: 0 } };
        if (c.method === "patch") return { data: employee() };
    });
    renderRoute("/directory/e1", { role: "HR" });
    fireEvent.click(await screen.findByRole("button", { name: "Ubah profil" }));
    const dialog = screen.getByRole("dialog", { name: "Ubah profil" });
    fireEvent.change(within(dialog).getByLabelText("Status kerja"), { target: { value: "PERMANENT" } });
    fireEvent.change(within(dialog).getByLabelText("Awal kontrak"), { target: { value: "2026-01-01" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "patch")).toBe(true));
    expect(calls.find((c) => c.method === "patch")!.data).toMatchObject({
      employment_type: "PERMANENT",
      contract_start: "2026-01-01",
      contract_end: null,
    });
  });
});


