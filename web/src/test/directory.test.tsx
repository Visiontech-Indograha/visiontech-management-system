import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const page = (items: unknown[]) => ({ items, total: items.length, page: 1, size: 25 });
const employee = (id = "e1") => ({
  id,
  employee_no: "VT-001",
  full_name: "Test User",
  position: "Teknisi",
  join_date: "2024-01-01",
  email: null,
  phone: null,
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

    expect(calls[0].url).toBe("/employees");

    fireEvent.change(screen.getByLabelText("Cari nama atau no. karyawan"), { target: { value: "test" } });
    await waitFor(() => expect(calls.length).toBeGreaterThan(1));

    fireEvent.change(screen.getByLabelText("Filter akun"), { target: { value: "inactive" } });
    await waitFor(() => expect(calls.length).toBeGreaterThan(2));
  });

  it("membuka detail dari daftar tanpa GET /employees/{id}", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees") return { data: page([employee()]) };
      if (c.url === "/employees/e1/documents") return { data: { items: [doc()], total: 1 } };
    });
    renderRoute("/directory", { role: "HR" });
    fireEvent.click(await screen.findByRole("link", { name: "Test User" }));
    expect(await screen.findByText("KTP")).toBeInTheDocument();
    expect(screen.getByText("Teknisi")).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/employees/e1")).toBe(false);
  });
});

describe("halaman detail karyawan (HR)", () => {
  it("dibuka langsung lewat tautan memuat karyawan dari GET /employees/{id}", async () => {
    mockApi((c) => {
      if (c.url === "/employees/e1") return { data: employee() };
      if (c.url === "/employees/e1/documents") return { data: { items: [], total: 0 } };
    });
    renderRoute("/directory/e1", { role: "HR" });
    expect(await screen.findByText("Test User")).toBeInTheDocument();
  });

  it("menambah berkas mengirim form ke upload lalu ke documents", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees") return { data: page([employee()]) };
      if (c.url === "/employees/e1/documents" && c.method === "get") return { data: { items: [], total: 0 } };
      if (c.url === "/files/upload" && c.method === "post") return { data: { file_id: "f1", message: "Berkas berhasil diunggah." } };
      if (c.url === "/employees/e1/documents" && c.method === "post") return { status: 201, data: doc({ id: "d2" }) };
    });
    renderRoute("/directory", { role: "HR" });
    fireEvent.click(await screen.findByRole("link", { name: "Test User" }));
    fireEvent.click(await screen.findByRole("button", { name: "Tambah berkas" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah berkas" });

    // Jenis baku dipilih, bukan diketik — aturan SIM pengemudi mencocokkan "SIM A"/"SIM C" persis.
    const docType = within(dialog).getByRole("combobox", { name: /Jenis dokumen/ });
    expect(within(docType).getByRole("option", { name: "SIM A" })).toBeInTheDocument();
    expect(within(docType).getByRole("option", { name: "Lainnya…" })).toBeInTheDocument();
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

  it("ubah profil mengirim PUT /employees/{id} dengan EmployeeUpdate", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees" && c.method === "get") return { data: page([employee()]) };
      if (c.url === "/employees/e1/documents" && c.method === "get") return { data: { items: [], total: 0 } };
      if (c.url === "/employees/e1" && c.method === "put") return { data: { ...employee(), phone: "0812" } };
    });
    renderRoute("/directory", { role: "HR" });
    fireEvent.click(await screen.findByRole("link", { name: "Test User" }));
    fireEvent.click(await screen.findByRole("button", { name: "Ubah profil" }));
    const dialog = screen.getByRole("dialog", { name: "Ubah profil" });
    fireEvent.change(within(dialog).getByLabelText("No. telepon"), { target: { value: "0812" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal lahir"), { target: { value: "1990-05-01" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "put")).toBe(true));
    expect(calls.find((c) => c.method === "put")!.data).toEqual({
      full_name: "Test User",
      email: null,
      phone: "0812",
      birth_date: "1990-05-01",
      address: null,
      emergency_contact: null,
    });
  });

  it("validasi zod: nama kosong dan email salah tidak dikirim", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees" && c.method === "get") return { data: page([employee()]) };
      if (c.url === "/employees/e1/documents") return { data: { items: [], total: 0 } };
    });
    renderRoute("/directory", { role: "HR" });
    fireEvent.click(await screen.findByRole("link", { name: "Test User" }));
    fireEvent.click(await screen.findByRole("button", { name: "Ubah profil" }));
    const dialog = screen.getByRole("dialog", { name: "Ubah profil" });
    fireEvent.change(within(dialog).getByLabelText("Nama lengkap"), { target: { value: " " } });
    fireEvent.change(within(dialog).getByLabelText("Email"), { target: { value: "bukan-email" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByText("Nama wajib diisi.")).toBeInTheDocument();
    expect(within(dialog).getByText("Format email tidak valid.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "put")).toBe(false);
  });
});

describe("R8 · perpanjang berkas dari daftar (termasuk Berkas saya)", () => {
  it("karyawan memperpanjang SIM dari profilnya: jenis tetap, supersedes_id terkirim", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees/e-lead/documents" && c.method === "get")
        return {
          data: {
            items: [
              doc({ id: "d1", employee_id: "e-lead", doc_type: "SIM A", status: "VERIFIED", lifecycle: "CURRENT" }),
              doc({ id: "d2", employee_id: "e-lead", doc_type: "MCU", status: "PENDING", lifecycle: "PENDING" }),
            ],
            total: 2,
          },
        };
      if (c.url === "/files/upload") return { data: { file_id: "f9", message: "ok" } };
      if (c.url === "/employees/e-lead/documents" && c.method === "post") return { status: 201, data: doc({ id: "d3" }) };
    });
    renderRoute("/my-documents", { role: "field" });

    fireEvent.click(await screen.findByRole("button", { name: "Perpanjang SIM A" }));
    expect(screen.queryByRole("button", { name: "Perpanjang MCU" })).toBeNull(); // belum terverifikasi
    const dialog = screen.getByRole("dialog", { name: "Perpanjang berkas" });
    expect(within(dialog).queryByRole("combobox", { name: /Jenis dokumen/ })).toBeNull(); // jenis tidak bisa diganti
    fireEvent.change(within(dialog).getByLabelText(/Nomor dokumen/), { target: { value: "987654321" } });
    fireEvent.change(within(dialog).getByLabelText(/Tanggal kedaluwarsa/), { target: { value: "2031-01-01" } });
    const fileInput = within(dialog).getByLabelText(/File/);
    Object.defineProperty(fileInput, "files", { value: [new File(["x"], "sim.png", { type: "image/png" })] });
    fireEvent.change(fileInput);
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));

    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/employees/e-lead/documents")).toBe(true));
    expect(calls.find((c) => c.method === "post" && c.url === "/employees/e-lead/documents")!.data).toEqual({
      doc_type: "SIM A",
      number: "987654321",
      expiry_date: "2031-01-01",
      file_id: "f9",
      supersedes_id: "d1",
    });
  });

  it("HR juga melihat Perpanjang di daftar berkas karyawan", async () => {
    mockApi((c) => {
      if (c.url === "/employees/e1") return { data: employee() };
      if (c.url === "/employees/e1/documents") return { data: { items: [doc({ status: "VERIFIED", lifecycle: "EXPIRED" })], total: 1 } };
    });
    renderRoute("/directory/e1", { role: "HR" });
    expect(await screen.findByRole("button", { name: "Perpanjang KTP" })).toBeInTheDocument();
  });
});

describe("mutasi / promosi & riwayat jabatan (M2, domain.js PROMOTE)", () => {
  const units = [
    { id: "u1", code: "CCTV", name: "CCTV & ACS" },
    { id: "u2", code: "WALLD", name: "Wall Display" },
  ];
  const history = [
    { id: "a2", employee_id: "e1", position: "Teknisi", unit_id: "u1", unit_name: "CCTV & ACS", valid_from: "2025-01-01", valid_to: null },
    { id: "a1", employee_id: "e1", position: "Helper", unit_id: "u1", unit_name: "CCTV & ACS", valid_from: "2024-01-01", valid_to: "2025-01-01" },
  ];
  const api = (extra?: (url: string, method: string) => { status?: number; data?: unknown } | undefined) =>
    mockApi((c) => {
      const hit = extra?.(c.url ?? "", c.method ?? "get");
      if (hit) return hit;
      if (c.url === "/employees/e1") return { data: { ...employee(), unit_id: "u1" } };
      if (c.url === "/employees/e1/documents") return { data: { items: [], total: 0 } };
      if (c.url === "/employees/e1/assignments" && c.method === "get") return { data: history };
      if (c.url === "/units") return { data: units };
    });

  it("HR melihat unit & riwayat, lalu memutasi ke unit lain", async () => {
    const calls = api((url, method) =>
      url === "/employees/e1/assignments" && method === "post"
        ? { data: { ...history[0], id: "a3", position: "Supervisor", unit_id: "u2", unit_name: "Wall Display", valid_from: "2026-10-01" } }
        : undefined,
    );
    renderRoute("/directory/e1", { role: "HR" });

    const riwayat = await screen.findByRole("region", { name: "Riwayat jabatan" });
    expect(await within(riwayat).findByText("Helper")).toBeInTheDocument();
    expect(within(riwayat).getByText(/sekarang/)).toBeInTheDocument();
    expect(await screen.findByText("CCTV & ACS", { selector: "dd" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Mutasi / promosi" }));
    const dialog = screen.getByRole("dialog", { name: "Mutasi / promosi" });
    fireEvent.change(within(dialog).getByLabelText("Jabatan"), { target: { value: "Supervisor" } });
    await within(dialog).findByRole("option", { name: "Wall Display" });
    fireEvent.change(within(dialog).getByLabelText("Unit"), { target: { value: "u2" } });
    fireEvent.change(within(dialog).getByLabelText("Berlaku mulai"), { target: { value: "2026-10-01" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(calls.find((c) => c.method === "post")!.data).toEqual({ position: "Supervisor", unit_id: "u2", valid_from: "2026-10-01" });
  });

  it("mutasi lintas unit ditolak API (masih bertugas di SK aktif): pesan tampil di dialog", async () => {
    api((url, method) =>
      url === "/employees/e1/assignments" && method === "post"
        ? apiError(409, "INVALID_STATE", "Mutasi lintas unit diblokir sampai penugasan aktif diserahterimakan.")
        : undefined,
    );
    renderRoute("/directory/e1", { role: "HR" });
    fireEvent.click(await screen.findByRole("button", { name: "Mutasi / promosi" }));
    const dialog = screen.getByRole("dialog", { name: "Mutasi / promosi" });
    await within(dialog).findByRole("option", { name: "Wall Display" });
    fireEvent.change(within(dialog).getByLabelText("Unit"), { target: { value: "u2" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Mutasi lintas unit diblokir");
  });

  it("peran tanpa manage:users tidak melihat tombol mutasi", async () => {
    api();
    renderRoute("/directory/e1", { role: "FINANCE" });
    await screen.findByRole("region", { name: "Riwayat jabatan" });
    expect(screen.queryByRole("button", { name: "Mutasi / promosi" })).toBeNull();
  });
});

describe("Berkas saya: karyawan mengajukan dokumen sendiri (M2)", () => {
  it("tombol Tambah berkas tersedia dan dokumen dikirim atas nama karyawan sendiri", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees/e-lead/documents" && c.method === "get") return { data: { items: [], total: 0 } };
      if (c.url === "/files/upload") return { data: { file_id: "f7", message: "ok" } };
      if (c.url === "/employees/e-lead/documents" && c.method === "post") return { status: 201, data: doc({ id: "d9" }) };
    });
    renderRoute("/my-documents", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah berkas" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah berkas" });
    fireEvent.change(within(dialog).getByLabelText(/Jenis dokumen/), { target: { value: "MCU" } });
    fireEvent.change(within(dialog).getByLabelText(/Nomor dokumen/), { target: { value: "MCU-2026-01" } });
    const fileInput = within(dialog).getByLabelText(/File/);
    Object.defineProperty(fileInput, "files", { value: [new File(["x"], "mcu.pdf", { type: "application/pdf" })] });
    fireEvent.change(fileInput);
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/employees/e-lead/documents")).toBe(true));
    expect(calls.find((c) => c.method === "post" && c.url === "/employees/e-lead/documents")!.data).toMatchObject({
      doc_type: "MCU", number: "MCU-2026-01", file_id: "f7",
    });
  });
});

