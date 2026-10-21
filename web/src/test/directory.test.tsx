import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

const page = (items: unknown[]) => ({ items, total: items.length, page: 1, size: 25 });
const employee = (id = "e1") => ({
  employee_id: id,
  employee_no: "VT-001",
  full_name: "Test User",
  office_id: "o1",
  office_name: "Kantor Pusat",
  division_id: "u1",
  division_name: "CCTV & ACS",
  position_id: "p1",
  position_code: "TEK",
  position_name: "Teknisi",
  join_date: "2024-01-01",
  pkwt_end_date: null,
  photo_file_id: null,
  face_enrolled: false,
  offboarding_status: "active",
  archived: false,
  email: null,
  addresses: [],
});
const masters = (url: string) => {
  if (url === "/offices") return { data: [{ id: "o1", name: "Kantor Pusat" }] };
  if (url === "/divisions") return { data: [{ id: "u1", code: "CCTV", name: "CCTV & ACS" }] };
  if (url === "/job-positions")
    return { data: [{ position_id: "p1", division_id: null, code: "TEK", name: "Teknisi", status: true }] };
};
const doc = (overrides: Record<string, unknown> = {}) => ({
  id: "d1",
  employee_id: "e1",
  doc_type: "KTP",
  status: "active",
  active_at: "2024-01-01",
  expired_at: "2025-01-01",
  file_id: "f1",
  created_at: "2024-01-01T00:00:00Z",
  ...overrides,
});

describe("halaman direktori utama", () => {
  it("menampilkan daftar", async () => {
    mockApi((c) => (c.url === "/employees" ? { data: page([employee()]) } : undefined));
    renderRoute("/directory", { role: "HR" });
    expect(await screen.findByText("Test User")).toBeInTheDocument();
  });

  it("filter cari & status kerja dikirim ke server", async () => {
    const calls = mockApi((c) => (c.url === "/employees" ? { data: page([]) } : undefined));
    renderRoute("/directory", { role: "HR" });
    await screen.findByText("Tidak ada karyawan yang cocok.");
    // Lonceng notifikasi ikut memanggil /notifications; yang diperiksa hanya panggilan daftar karyawan.
    expect(calls.find((c) => c.url === "/employees")).toBeDefined();

    fireEvent.change(screen.getByLabelText("Cari nama atau no. karyawan"), { target: { value: "test" } });
    await waitFor(() => expect(calls.length).toBeGreaterThan(1));

    fireEvent.change(screen.getByLabelText("Filter status"), { target: { value: "offboarded" } });
    await waitFor(() => expect(calls.length).toBeGreaterThan(2));
  });

  it("membuka detail dari daftar: baris daftar tampil dulu, detail dari GET /employees/{id}", async () => {
    mockApi((c) => {
      if (c.url === "/employees") return { data: page([employee()]) };
      if (c.url === "/employees/e1") return { data: employee() };
      if (c.url === "/employees/e1/documents") return { data: { items: [doc()], total: 1 } };
    });
    renderRoute("/directory", { role: "HR" });
    fireEvent.click(await screen.findByRole("link", { name: "Test User" }));
    expect(await screen.findByText("KTP")).toBeInTheDocument();
    expect(screen.getAllByText("Teknisi").length).toBeGreaterThan(0);
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
    expect(screen.getByText("Email")).toBeInTheDocument();
    expect(screen.getByText("Alamat")).toBeInTheDocument();
  });

  it("rekan kerja tidak melihat email & alamat, hanya catatan", async () => {
    mockApi((c) => {
      if (c.url === "/employees/e1") return { data: employee() };
    });
    renderRoute("/directory/e1", { role: "field" });
    expect(await screen.findByText("Test User")).toBeInTheDocument();
    expect(screen.queryByText("Email")).toBeNull();
    expect(screen.getByText(/hanya terlihat oleh pemilik serta HR/)).toBeInTheDocument();
  });

  it("menambah berkas mengirim form ke upload lalu ke documents", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees") return { data: page([employee()]) };
      if (c.url === "/employees/e1") return { data: employee() };
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

  it("ubah data mengirim PUT /employees/{id} dengan EmployeeUpdate V2", async () => {
    const calls = mockApi((c) => {
      const m = masters(c.url ?? "");
      if (m) return m;
      if (c.url === "/employees/e1" && c.method === "get") return { data: employee() };
      if (c.url === "/employees/e1/documents" && c.method === "get") return { data: { items: [], total: 0 } };
      if (c.url === "/employees/e1" && c.method === "put") return { data: { ...employee(), pkwt_end_date: "2027-01-01" } };
    });
    renderRoute("/directory/e1", { role: "HR" });
    fireEvent.click(await screen.findByRole("button", { name: "Ubah data" }));
    const dialog = screen.getByRole("dialog", { name: "Ubah data karyawan" });
    await within(dialog).findByRole("option", { name: "Kantor Pusat" });
    fireEvent.change(within(dialog).getByLabelText("Akhir PKWT"), { target: { value: "2027-01-01" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "put")).toBe(true));
    expect(calls.find((c) => c.method === "put")!.data).toEqual({
      employee_no: "VT-001",
      full_name: "Test User",
      office_id: "o1",
      division_id: "u1",
      position_id: "p1",
      join_date: "2024-01-01",
      pkwt_end_date: "2027-01-01",
    });
  });

  it("validasi zod: nama kosong & akhir PKWT sebelum bergabung tidak dikirim", async () => {
    const calls = mockApi((c) => {
      const m = masters(c.url ?? "");
      if (m) return m;
      if (c.url === "/employees/e1" && c.method === "get") return { data: employee() };
      if (c.url === "/employees/e1/documents") return { data: { items: [], total: 0 } };
    });
    renderRoute("/directory/e1", { role: "HR" });
    fireEvent.click(await screen.findByRole("button", { name: "Ubah data" }));
    const dialog = screen.getByRole("dialog", { name: "Ubah data karyawan" });
    fireEvent.change(within(dialog).getByLabelText("Nama lengkap"), { target: { value: " " } });
    fireEvent.change(within(dialog).getByLabelText("Akhir PKWT"), { target: { value: "2023-01-01" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByText("Nama lengkap minimal 2 karakter.")).toBeInTheDocument();
    expect(within(dialog).getByText("Akhir PKWT tidak boleh sebelum tanggal bergabung.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "put")).toBe(false);
  });
});

describe("berkas karyawan dikelola HR/GA (M3, employee_file)", () => {
  it("HR memperbarui SIM dari daftar: jenis tetap, tanpa nomor/supersedes", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees/e1") return { data: employee() };
      if (c.url === "/employees/e1/documents" && c.method === "get")
        return {
          data: {
            items: [
              doc({ id: "d1", doc_type: "SIM_A", status: "active" }),
              doc({ id: "d2", doc_type: "MCU", status: "extended" }),
            ],
            total: 2,
          },
        };
      if (c.url === "/files/upload") return { data: { file_id: "f9", message: "ok" } };
      if (c.url === "/employees/e1/documents" && c.method === "post") return { status: 201, data: doc({ id: "d3" }) };
    });
    renderRoute("/directory/e1", { role: "HR" });

    fireEvent.click(await screen.findByRole("button", { name: "Perbarui SIM A" }));
    expect(screen.queryByRole("button", { name: "Perbarui Medical check-up" })).toBeNull(); // sudah diganti
    const dialog = screen.getByRole("dialog", { name: "Perbarui berkas" });
    expect(within(dialog).queryByRole("combobox", { name: /Jenis dokumen/ })).toBeNull();
    fireEvent.change(within(dialog).getByLabelText(/Tanggal kedaluwarsa/), { target: { value: "2031-01-01" } });
    const fileInput = within(dialog).getByLabelText(/File/);
    Object.defineProperty(fileInput, "files", { value: [new File(["x"], "sim.png", { type: "image/png" })] });
    fireEvent.change(fileInput);
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));

    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/employees/e1/documents")).toBe(true));
    expect(calls.find((c) => c.method === "post" && c.url === "/employees/e1/documents")!.data).toEqual({
      doc_type: "SIM_A",
      file_id: "f9",
      active_at: null,
      expired_at: "2031-01-01",
    });
  });

  it("HR menonaktifkan dokumen yang berlaku", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees/e1") return { data: employee() };
      if (c.url === "/employees/e1/documents") return { data: { items: [doc()], total: 1 } };
      if (c.url === "/employees/e1/documents/d1/deactivate") return { data: doc({ status: "not_active" }) };
    });
    renderRoute("/directory/e1", { role: "HR" });
    fireEvent.click(await screen.findByRole("button", { name: "Nonaktifkan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/employees/e1/documents/d1/deactivate")).toBe(true));
  });
});

describe("Berkas saya: karyawan hanya melihat (M3)", () => {
  it("tanpa tombol Tambah/Perbarui; dokumennya sendiri tampil", async () => {
    mockApi((c) =>
      c.url === "/employees/e-lead/documents" ? { data: { items: [doc({ doc_type: "SIM_C" })], total: 1 } } : undefined,
    );
    renderRoute("/my-documents", { role: "field" });
    expect(await screen.findByText("SIM C")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tambah berkas" })).toBeNull();
    expect(screen.queryByRole("button", { name: /Perbarui/ })).toBeNull();
  });
});

describe("peringatan masa berlaku di daftar berkas (M3)", () => {
  it("≤ 30 hari dan kedaluwarsa ditandai; yang masih lama tidak", async () => {
    const inDays = (n: number) => {
      const d = new Date(Date.now() + n * 86_400_000);
      return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(d);
    };
    mockApi((c) =>
      c.url === "/employees/e-lead/documents"
        ? {
            data: {
              items: [
                doc({ id: "a", doc_type: "SIM_A", expired_at: inDays(10) }),
                doc({ id: "b", doc_type: "MCU", expired_at: inDays(-3) }),
                doc({ id: "c", doc_type: "KTP", expired_at: inDays(400) }),
              ],
              total: 3,
            },
          }
        : undefined,
    );
    renderRoute("/my-documents", { role: "field" });
    expect(await screen.findByText("10 hari lagi")).toBeInTheDocument();
    const mcuRow = screen.getByText("Medical check-up").closest("tr") as HTMLElement;
    expect(within(mcuRow).getByText("Kedaluwarsa")).toBeInTheDocument();
    expect(screen.queryByText(/400 hari/)).toBeNull();
  });
});


describe("siklus karyawan oleh HR (M2-02, M2-03)", () => {
  it("Tambah karyawan: validasi lalu POST /employees", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees" && c.method === "get") return { data: { items: [], total: 0, page: 1, size: 25 } };
      const m = masters(c.url ?? "");
      if (m) return m;
      if (c.url === "/employees" && c.method === "post") return { data: employee("e9") };
      if (c.url === "/employees/e9") return { data: employee("e9") };
    });
    renderRoute("/directory", { role: "HR" });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah karyawan" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah karyawan" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByText("Nama lengkap minimal 2 karakter.")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("No. karyawan"), { target: { value: "VT-099" } });
    fireEvent.change(within(dialog).getByLabelText("Nama lengkap"), { target: { value: "Karyawan Baru" } });
    await within(dialog).findByRole("option", { name: "Kantor Pusat" });
    fireEvent.change(within(dialog).getByLabelText("Kantor"), { target: { value: "o1" } });
    fireEvent.change(within(dialog).getByLabelText("Divisi"), { target: { value: "u1" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/employees" && c.method === "post")).toBe(true));
    const body = calls.find((c) => c.url === "/employees" && c.method === "post")!.data as Record<string, unknown>;
    expect(body).toMatchObject({
      employee_no: "VT-099", full_name: "Karyawan Baru", office_id: "o1", division_id: "u1", position_id: null, address: null,
    });
  });

  it("Offboarding (M9): memulai proses clearance lewat POST /offboarding, bukan menonaktifkan langsung", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees/e1") return { data: employee() };
      if (c.url === "/offboarding" && c.method === "post") return { data: { clearance_items: [{}, {}] } };
    });
    renderRoute("/directory/e1", { role: "HR" });
    fireEvent.click(await screen.findByRole("button", { name: "Offboarding" }));
    const dialog = screen.getByRole("dialog", { name: "Offboarding Test User" });
    fireEvent.change(within(dialog).getByLabelText("Alasan"), { target: { value: "RESIGN" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Mulai offboarding" }));
    expect(await within(dialog).findByText("Isi tanggal efektif.")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Tanggal efektif"), { target: { value: "2026-11-30" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Mulai offboarding" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/offboarding" && c.method === "post")).toBe(true));
    expect(calls.find((c) => c.url === "/offboarding")!.data).toEqual({
      employee_id: "e1", reason_type: "RESIGN", effective_date: "2026-11-30", notes: null,
    });
    expect(calls.some((c) => c.url.endsWith("/offboard"))).toBe(false);
  });

  it("bukan HR: tidak ada tombol Tambah karyawan", async () => {
    mockApi((c) => {
      if (c.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 25 } };
    });
    renderRoute("/directory", { role: "field" });
    await screen.findByRole("heading", { name: "Direktori" });
    expect(screen.queryByRole("button", { name: "Tambah karyawan" })).toBeNull();
  });
});

describe("akun login karyawan (M1-01)", () => {
  it("HR membuat akun; password sementara tampil sekali", async () => {
    let exists = false;
    const calls = mockApi((c) => {
      if (c.url === "/employees/e1") return { data: employee() };
      if (c.url === "/employees/e1/account" && c.method === "get")
        return { data: exists ? { exists: true, login: "baru@contoh.id", is_active: true, last_login_at: null } : { exists: false } };
      if (c.url === "/employees/e1/account" && c.method === "post") {
        exists = true;
        return { data: { exists: true, login: "baru@contoh.id", is_active: true, temporary_password: "Sementara123" } };
      }
    });
    renderRoute("/directory/e1", { role: "HR" });
    expect(await screen.findByText("Karyawan ini belum punya akun login.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Email login"), { target: { value: "baru@contoh.id" } });
    fireEvent.click(screen.getByRole("button", { name: "Buat akun" }));
    expect(await screen.findByText("Sementara123")).toBeInTheDocument();
    expect(calls.find((c) => c.url === "/employees/e1/account" && c.method === "post")!.data).toEqual({ login: "baru@contoh.id" });
  });

  it("HR melihat penanda akun terkunci karena gagal login (R-21)", async () => {
    mockApi((c) => {
      if (c.url === "/employees/e1") return { data: employee() };
      if (c.url === "/employees/e1/account")
        return {
          data: {
            exists: true, login: "a@contoh.id", is_active: true, last_login_at: null,
            failed_logins: 5, locked_until: new Date(Date.now() + 600_000).toISOString(),
          },
        };
    });
    renderRoute("/directory/e1", { role: "HR" });
    expect(await screen.findByTestId("account-locked")).toHaveTextContent("5 kali gagal login");
  });
});

describe("alamat karyawan (1─N, V2)", () => {
  it("HR melihat alamat dan menambah alamat baru", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/employees/e1")
        return { data: { ...employee(), addresses: [{ address_id: "a1", address_line: "Jl. Mawar 12", city: "Bandung", postal_code: "40111" }] } };
      if (c.url === "/employees/e1/addresses" && c.method === "post")
        return { status: 201, data: { address_id: "a2", ...(c.data as Record<string, unknown>) } };
    });
    renderRoute("/directory/e1", { role: "HR" });
    expect(await screen.findByText("Jl. Mawar 12, Bandung 40111")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tambah alamat" }));
    fireEvent.change(screen.getByLabelText("Kota"), { target: { value: "Jakarta" } });
    fireEvent.change(screen.getByLabelText("Kode pos"), { target: { value: "10110" } });
    fireEvent.change(screen.getAllByLabelText("Alamat").slice(-1)[0], { target: { value: "Jl. Melati 3" } });
    fireEvent.click(screen.getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/employees/e1/addresses" && c.method === "post")).toBe(true));
    expect(calls.find((c) => c.url === "/employees/e1/addresses")!.data).toEqual({
      address_line: "Jl. Melati 3", city: "Jakarta", postal_code: "10110",
    });
  });
});
