import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { apiError, mockApi, renderRoute } from "./utils";

const page = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 25 });

const employee = (over: Record<string, unknown> = {}) => ({
  id: "e1",
  username: "budi",
  full_name: "Budi Santoso",
  role: "user",
  user_type: "DRIVER",
  is_active: true,
  employment_type: "CONTRACT",
  phone: null,
  employee_no: null,
  join_date: null,
  contract_start: null,
  contract_end: null,
  resign_date: null,
  description: null,
  documents_status: null,
  documents_missing: null,
  ...over,
});

const missing = [
  { id: "t1", code: "KTP", name: "KTP" },
  { id: "t2", code: "SIM_A", name: "SIM A" },
];

describe("direktori", () => {
  it("HES melihat kolom kelengkapan berkas", async () => {
    mockApi((c) => {
      if (c.url === "/employees")
        return { data: page([employee({ documents_status: "INCOMPLETE", documents_missing: missing })]) };
    });
    renderRoute("/directory", { role: "hes" });
    expect(await screen.findByText("Budi Santoso")).toBeInTheDocument();
    expect(screen.getByText("Berkas", { selector: "th" })).toBeInTheDocument();
    expect(screen.getByText("Kurang 2 berkas")).toBeInTheDocument();
  });

  it("Finance tidak melihat kolom kelengkapan", async () => {
    mockApi((c) => (c.url === "/employees" ? { data: page([employee()]) } : undefined));
    renderRoute("/directory", { role: "finance" });
    expect(await screen.findByText("Budi Santoso")).toBeInTheDocument();
    expect(screen.queryByText("Berkas", { selector: "th" })).toBeNull();
  });

  it("filter dan status default 'Aktif' dikirim ke server", async () => {
    const calls = mockApi((c) => (c.url === "/employees" ? { data: page([]) } : undefined));
    renderRoute("/directory", { role: "hes" });
    await screen.findByText("Tidak ada karyawan yang cocok.");
    expect(calls[0]).toBeDefined();
    fireEvent.change(screen.getByLabelText("Filter akun"), { target: { value: "inactive" } });
    await waitFor(() => expect(calls.length).toBeGreaterThan(1));
  });
});

describe("perlu dilengkapi", () => {
  it("menampilkan berkas yang kurang dan tautan unggah", async () => {
    mockApi((c) =>
      c.url === "/documents/incomplete"
        ? {
            data: [
              {
                user_id: "e1",
                full_name: "Budi Santoso",
                role: "user",
                user_type: "DRIVER",
                employment_type: "CONTRACT",
                missing: missing,
                missing_count: 2,
                nearest_expiry: "2026-10-01",
              },
            ],
          }
        : undefined,
    );
    renderRoute("/documents/incomplete", { role: "hes" });
    expect(await screen.findByText("KTP, SIM A")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Unggah berkas" })).toHaveAttribute("href", "/directory/e1");
    expect(screen.getByText("1 Okt 2026")).toBeInTheDocument();
  });

  it("keadaan kosong", async () => {
    mockApi((c) => (c.url === "/documents/incomplete" ? { data: [] } : undefined));
    renderRoute("/documents/incomplete", { role: "hes" });
    expect(await screen.findByText("Semua berkas wajib sudah lengkap.")).toBeInTheDocument();
  });

  it("role selain HES/SA ditolak", () => {
    mockApi(() => undefined);
    expect(renderRoute("/documents/incomplete", { role: "admin" }).router.state.location.pathname).toBe("/forbidden");
  });
});

describe("detail karyawan dan berkas", () => {
  const doc = (over: Record<string, unknown> = {}) => ({
    id: "d1",
    user_id: "e1",
    document_type_id: "t3",
    type_name: "MCU",
    custom_label: null,
    document_number: "MCU-1",
    issued_at: null,
    expires_at: "2026-09-25",
    file_id: "f1",
    file_url: "/api/v1/files/f1",
    notes: null,
    expiry_level: "CRITICAL",
    days_left: 4,
    created_at: "2026-09-01T00:00:00Z",
    ...over,
  });

  const handler = (extra?: (c: { url?: string; method?: string }) => unknown) => (c: { url?: string; method?: string }) => {
    if (extra) {
      const r = extra(c);
      if (r) return r as { data?: unknown; status?: number };
    }
    if (c.url?.startsWith("/files/") && c.url.endsWith("/url?variant=thumb")) {
      return { data: { url: `https://mock.url${c.url.split("?")[0]}.pdf`, mime_type: "application/pdf" } };
    }
    if (c.url?.startsWith("/files/") && c.url.endsWith("/url?variant=full")) {
      return { data: { url: `https://mock.url${c.url.split("?")[0]}_full.pdf`, mime_type: "application/pdf" } };
    }
    if (c.url === "/employees/e1" && c.method === "get")
      return { data: employee({ documents_status: "INCOMPLETE", documents_missing: missing }) };
    if (c.url === "/employees/e1/documents" && c.method === "get") return { data: [doc()] };
    if (c.url === "/document-types")
      return {
        data: [
          { id: "t3", code: "MCU", name: "MCU", has_expiry: true, is_active: true, sort_order: 0, rules: [] },
          { id: "t1", code: "KTP", name: "KTP", has_expiry: false, is_active: true, sort_order: 1, rules: [] },
        ],
      };
  };

  it("menampilkan profil, kekurangan berkas, dan badge kedaluwarsa", async () => {
    mockApi(handler() as never);
    renderRoute("/directory/e1", { role: "hes" });
    expect(await screen.findByText("MCU", { selector: "td" })).toBeInTheDocument();
    expect(screen.getByText("≤ 7 hari")).toBeInTheDocument();
    expect(screen.getByText(/Berkas wajib yang kurang: KTP, SIM A/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Unduh MCU" })).toBeInTheDocument();
  });

  it("Finance melihat profil tetapi tidak tab berkas", async () => {
    mockApi(handler() as never);
    renderRoute("/directory/e1", { role: "finance" });
    expect(await screen.findByRole("heading", { name: "Budi Santoso" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Berkas" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Ubah profil" })).toBeNull();
  });

  it("menambah berkas mengirim multipart; galat server tampil pada field", async () => {
    let n = 0;
    const calls = mockApi(
      handler((c) => {
        if (c.url === "/employees/e1/documents" && c.method === "post") {
          n += 1;
          return n === 1
            ? apiError(422, "VALIDATION_ERROR", "x", { fields: { expires_at: "Tanggal kedaluwarsa wajib untuk jenis berkas ini." } })
            : { status: 201, data: doc({ id: "d2" }) };
        }
      }) as never,
    );
    renderRoute("/directory/e1", { role: "hes" });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah berkas" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah berkas" });
    await within(dialog).findByRole("option", { name: /MCU/ });
    fireEvent.change(within(dialog).getByLabelText("Jenis berkas"), { target: { value: "t3" } });
    fireEvent.change(within(dialog).getByLabelText("Nomor"), { target: { value: "MCU-2" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Tanggal kedaluwarsa wajib untuk jenis berkas ini.")).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText(/Tanggal kedaluwarsa/), { target: { value: "2027-01-01" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const posts = calls.filter((c) => c.method === "post");
    expect(posts[1].data).toMatchObject({ document_type_id: "t3", document_number: "MCU-2", expires_at: "2027-01-01" });
  });

  it("mode label bebas mengirim custom_label", async () => {
    const calls = mockApi(
      handler((c) => (c.method === "post" ? { status: 201, data: doc({ id: "d3" }) } : undefined)) as never,
    );
    renderRoute("/directory/e1", { role: "hes" });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah berkas" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah berkas" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Label bebas" }));
    fireEvent.change(within(dialog).getByLabelText("Label"), { target: { value: "Sertifikat Ketinggian" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post")).toBe(true));
    const body = calls.find((c) => c.method === "post")!.data as Record<string, unknown>;
    expect(body.custom_label).toBe("Sertifikat Ketinggian");
    expect(body.document_type_id).toBeUndefined();
  });

  it("mengosongkan catatan saat ubah berkas memakai 'clear'", async () => {
    const calls = mockApi(
      handler((c) => {
        if (c.url === "/employees/e1/documents" && c.method === "get") return { data: [doc({ notes: "asli" })] };
        if (c.method === "patch") return { data: doc() };
      }) as never,
    );
    renderRoute("/directory/e1", { role: "hes" });
    fireEvent.click(await screen.findByRole("button", { name: "Ubah" }));
    const dialog = await screen.findByRole("dialog", { name: "Ubah berkas" });
    // baris yang sudah punya file: tidak ada input file, ada petunjuk
    expect(within(dialog).getByText(/tambahkan baris berkas baru/)).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Catatan"), { target: { value: "" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "patch")).toBe(true));
    const patch = calls.find((c) => c.method === "patch")!;
    expect(patch.url).toBe("/employees/e1/documents/d1");
    expect((patch.data as Record<string, unknown>).clear).toBe("notes");
  });

  it("ubah profil mengirim status kerja dan tanggal", async () => {
    const calls = mockApi(handler((c) => (c.method === "patch" ? { data: employee() } : undefined)) as never);
    renderRoute("/directory/e1", { role: "hes" });
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

describe("jenis berkas", () => {
  const types = [
    {
      id: "t3",
      code: "MCU",
      name: "MCU",
      has_expiry: true,
      is_active: true,
      sort_order: 0,
      rules: [
        { role: "user", user_type: "WTL", employment_type: null },
        { role: null, user_type: null, employment_type: "CONTRACT" },
      ],
    },
    { id: "t4", code: "SIM_C", name: "SIM C", has_expiry: false, is_active: true, sort_order: 1, rules: [] },
  ];

  it("menampilkan aturan wajib dan 'Opsional'", async () => {
    mockApi((c) => (c.url === "/document-types" ? { data: types } : undefined));
    renderRoute("/master/document-types", { role: "hes" });
    expect(await screen.findByText("WTL; Semua role · Kontrak")).toBeInTheDocument();
    expect(screen.getByText("Opsional")).toBeInTheDocument();
  });

  it("membuat jenis dengan aturan", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/document-types" && c.method === "get") return { data: types };
      if (c.url === "/document-types" && c.method === "post") return { status: 201, data: types[0] };
    });
    renderRoute("/master/document-types", { role: "hes" });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah jenis" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah jenis berkas" });
    fireEvent.change(within(dialog).getByLabelText("Nama"), { target: { value: "Sertifikat K3" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Tambah aturan" }));
    fireEvent.change(within(dialog).getByLabelText("Kelompok aturan 1"), { target: { value: "user:DRIVER" } });
    fireEvent.change(within(dialog).getByLabelText("Status kerja aturan 1"), { target: { value: "CONTRACT" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post")).toBe(true));
    expect(calls.find((c) => c.method === "post")!.data).toMatchObject({
      name: "Sertifikat K3",
      rules: [{ role: "user", user_type: "DRIVER", employment_type: "CONTRACT" }],
    });
  });

  it("Admin tidak dapat membuka halaman", () => {
    mockApi(() => undefined);
    expect(renderRoute("/master/document-types", { role: "admin" }).router.state.location.pathname).toBe("/forbidden");
  });
});

describe("berkas saya dan banner", () => {
  const me = { ...mockMe("wtl")!, id: "e1", documents_incomplete: { count: 2, missing: ["KTP", "MCU"] } };

  it("banner non-blokir tampil pada semua halaman untuk pemilik", async () => {
    mockApi(() => undefined);
    renderRoute("/", { me });
    expect(await screen.findByText(/2 berkas belum lengkap: KTP, MCU/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Lihat berkas saya" })).toHaveAttribute("href", "/my-documents");
    expect(screen.getByText(/Selamat datang/)).toBeInTheDocument(); // tidak memblokir
  });

  it("tanpa berkas kurang tidak ada banner", () => {
    mockApi(() => undefined);
    renderRoute("/", { role: "wtl" });
    expect(screen.queryByText(/berkas belum lengkap/)).toBeNull();
  });

  it("halaman Berkas saya menampilkan kelengkapan dan berkas (tanpa tombol kelola)", async () => {
    mockApi((c) => {
      if (c.url === "/employees/e1/documents/completeness") return { data: { status: "INCOMPLETE", missing } };
      if (c.url === "/employees/e1/documents") return { data: [] };
    });
    renderRoute("/my-documents", { me });
    expect(await screen.findByText(/2 berkas belum lengkap: KTP, SIM A/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tambah berkas" })).toBeNull();
    expect(await screen.findByText("Belum ada berkas.")).toBeInTheDocument();
  });
});
