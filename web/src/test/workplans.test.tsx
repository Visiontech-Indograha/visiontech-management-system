import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const plan = (over: Record<string, unknown> = {}) => ({
  id: "p1",
  title: "Instalasi CCTV Gudang",
  unit_id: "u1",
  site_id: "s1",
  location_text: "Cikarang",
  description: "Pasang 6 kamera",
  category: "INSTALASI",
  period_start: "2026-10-01",
  period_end: "2026-10-02",
  pm_employee_id: "e-pm",
  leader_employee_id: "e-lead",
  number: null,
  status: "DRAFT",
  revision: 1,
  row_version: 3,
  cancellation_reason: null,
  appeal_reason: null,
  ...over,
});
const emp = (id: string, name: string, unit_id: string | null = "u1") => ({
  id,
  employee_no: id,
  full_name: name,
  position: "Teknisi",
  join_date: "2024-01-01",
  unit_id,
  is_active: true,
});
const employees = { items: [emp("e-pm", "Pak PM"), emp("e-lead", "Bu Ketua")], total: 2, page: 1, size: 100 };
const planDetail = (p: ReturnType<typeof plan>) => ({
  plan: { ...p, unit_name: "Infrastruktur", category_label: "Instalasi" },
  team: [
    { employee_id: "e-lead", full_name: "Bu Ketua", position: "Teknisi Senior", role_in_plan: "LEADER" },
    { employee_id: "e-member", full_name: "Pak Anggota", position: "Teknisi", role_in_plan: "MEMBER" },
  ],
  days: [
    { work_date: "2026-10-01", title: "Pasang", tasks: [{ title: "Pasang CCTV 1", description: "Area A", files: [] }] },
    { work_date: "2026-10-02", title: "Uji", tasks: [{ title: "Uji kamera", description: "Semua", files: [] }] },
  ],
  assets: [],
});
const formOptions = {
  unit_name: "Infrastruktur",
  categories: [
    { code: "INSTALASI", label: "Instalasi" },
    { code: "SURVEI", label: "Survei" },
  ],
  sites: [{ id: "s1", name: "Cikarang", description: null, lat: -6.2, lng: 106.8 }],
  leaders: [
    { id: "e-lead", full_name: "Bu Ketua", position: "Teknisi Senior" },
    { id: "e-member", full_name: "Pak Anggota", position: "Teknisi" },
  ],
  members: [
    { id: "e-lead", full_name: "Bu Ketua", position: "Teknisi Senior" },
    { id: "e-member", full_name: "Pak Anggota", position: "Teknisi" },
  ],
  tools: [{ id: "t1", kind: "TOOL", vehicle_type: null, code: "ALT-1", name: "Tangga" }],
  vehicles: [{ id: "v1", kind: "VEHICLE", vehicle_type: "CAR", code: "MOB-01", name: "Mobil 1" }],
};

describe("Work plan — daftar", () => {
  it("menampilkan kartu rencana kerja dan mengirim filter status", async () => {
    const calls = mockApi((c) => (c.url === "/work-plans" ? { data: [plan()] } : undefined));
    renderRoute("/work-plans", { role: "field" });
    expect(await screen.findByText("Instalasi CCTV Gudang")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Buat rencana kerja" })).toBeNull();
    fireEvent.change(screen.getByLabelText("Filter status"), { target: { value: "IN_PROGRESS" } });
    await waitFor(() =>
      expect(calls[calls.length - 1].params).toEqual({ archived: false, status_filter: "IN_PROGRESS" }),
    );
  });

  it("keadaan kosong dan galat", async () => {
    mockApi((c) => (c.url === "/work-plans" ? { data: [] } : undefined));
    const { unmount } = renderRoute("/work-plans", { role: "PM" });
    expect(await screen.findByText("Belum ada work plan yang dapat Anda lihat.")).toBeInTheDocument();
    unmount();
    mockApi(() => apiError(500, "INTERNAL_ERROR", "x"));
    renderRoute("/work-plans", { role: "PM" });
    expect(await screen.findByRole("button", { name: "Coba lagi" })).toBeInTheDocument();
  });

  it("draf terarsip dipulihkan dari daftar (restore)", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans") return { data: [plan()] };
      if (c.url === "/work-plans/p1/restore") return { data: plan({ row_version: 4 }) };
    });
    renderRoute("/work-plans", { role: "PM" });
    await screen.findByText("Instalasi CCTV Gudang");
    fireEvent.click(screen.getByLabelText("Tampilkan draf terarsip"));
    fireEvent.click(await screen.findByRole("button", { name: "Pulihkan draf" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/restore")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/p1/restore")!.data).toEqual({ row_version: 3, reason: "" });
  });

  it("Buat rencana kerja v2: satu permintaan POST /work-plans/full berisi hari, detail, tim, alat, kendaraan, driver", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans" && c.method === "get") return { data: [] };
      if (c.url === "/work-plans/form-options") return { data: formOptions };
      if (c.url === "/work-plans/driver-options") return { data: ["e-member"] };
      if (c.url === "/work-plans/full") return { status: 201, data: planDetail(plan()) };
      if (c.url === "/work-plans/p1") return { data: plan() };
      if (c.url === "/work-plans/p1/detail") return { data: planDetail(plan()) };
    });
    const { router } = renderRoute("/work-plans", { role: "PM" });
    fireEvent.click((await screen.findAllByRole("button", { name: "Buat rencana kerja" }))[0]);
    await waitFor(() => expect(router.state.location.pathname).toBe("/work-plans/new"));
    await screen.findByRole("option", { name: "Cikarang" });
    expect(screen.getByLabelText("Tipe")).toHaveValue("Infrastruktur");
    fireEvent.change(screen.getByLabelText("Judul pekerjaan"), { target: { value: "Instalasi CCTV Gudang" } });
    fireEvent.change(screen.getByLabelText("Deskripsi pekerjaan keseluruhan"), { target: { value: "Pasang 6 kamera" } });
    fireEvent.change(screen.getByLabelText("Kategori pekerjaan"), { target: { value: "INSTALASI" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Lokasi kerja" }), { target: { value: "s1" } });
    fireEvent.change(screen.getByLabelText("Tanggal mulai"), { target: { value: "2026-10-01" } });
    fireEvent.change(screen.getByLabelText("Tanggal selesai"), { target: { value: "2026-10-01" } });
    expect(await screen.findByText("Hari 1 · 1 Okt 2026")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tambah hari kerja" }));
    expect(await screen.findByText("Hari 2 · 2 Okt 2026")).toBeInTheDocument();
    const titles = screen.getAllByPlaceholderText("mis. Pemasangan CCTV 1");
    const descs = screen.getAllByPlaceholderText("mis. Memasang CCTV 1 di area A");
    fireEvent.change(titles[0], { target: { value: "Pasang CCTV 1" } });
    fireEvent.change(descs[0], { target: { value: "Area A" } });
    fireEvent.change(titles[1], { target: { value: "Uji kamera" } });
    fireEvent.change(descs[1], { target: { value: "Semua" } });
    fireEvent.change(screen.getByLabelText("Ketua tim"), { target: { value: "e-lead" } });
    // Ketua tidak muncul lagi di daftar anggota.
    await waitFor(() => expect(screen.queryByRole("checkbox", { name: /Bu Ketua/ })).toBeNull());
    fireEvent.click(screen.getByRole("checkbox", { name: /Pak Anggota/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Tangga/ }));
    fireEvent.change(screen.getByLabelText(/Kendaraan/), { target: { value: "v1" } });
    await screen.findByRole("option", { name: "Pak Anggota" });
    fireEvent.change(screen.getByLabelText("Driver"), { target: { value: "e-member" } });
    fireEvent.click(screen.getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/work-plans/p1"));
    expect(calls.filter((c) => c.method === "post")).toHaveLength(1);
    expect(calls.find((c) => c.url === "/work-plans/full")!.data).toEqual({
      title: "Instalasi CCTV Gudang",
      description: "Pasang 6 kamera",
      category: "INSTALASI",
      site_id: "s1",
      new_site: null,
      period_start: "2026-10-01",
      period_end: "2026-10-02",
      days: [
        { work_date: "2026-10-01", tasks: [{ title: "Pasang CCTV 1", description: "Area A", file_ids: [] }], site_id: null, member_employee_ids: null },
        { work_date: "2026-10-02", tasks: [{ title: "Uji kamera", description: "Semua", file_ids: [] }], site_id: null, member_employee_ids: null },
      ],
      leader_employee_id: "e-lead",
      member_employee_ids: ["e-member"],
      is_out_of_town: false,
      work_type_id: null,
      tool_ids: ["t1"],
      vehicle_id: "v1",
      driver_employee_id: "e-member",
      row_version: null,
    });
  });

  it("validasi Buat rencana kerja: wajib isi & tanggal selesai sebelum mulai", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/form-options") return { data: formOptions };
    });
    renderRoute("/work-plans/new", { role: "PM" });
    await screen.findByRole("option", { name: "Cikarang" });
    fireEvent.change(screen.getByLabelText("Tanggal mulai"), { target: { value: "2026-10-05" } });
    fireEvent.change(screen.getByLabelText("Tanggal selesai"), { target: { value: "2026-10-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Tanggal selesai tidak boleh sebelum tanggal mulai.")).toBeInTheDocument();
    expect(screen.getByText("Judul pekerjaan wajib diisi.")).toBeInTheDocument();
    expect(screen.getByText("Pilih ketua tim.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post")).toBe(false);
  });
});

describe("Work plan — detail & tindakan", () => {
  const detail = (p: ReturnType<typeof plan>, extra?: (url: string, method: string) => { status?: number; data?: unknown } | undefined) =>
    mockApi((c) => {
      const hit = extra?.(c.url ?? "", c.method ?? "get");
      if (hit) return hit;
      if (c.url === "/work-plans/p1") return { data: p };
      if (c.url === "/work-plans/p1/detail") return { data: planDetail(p) };
      if (c.url === "/employees") return { data: employees };
    });

  it("PM melihat isi rencana kerja dan tindakan draf, lalu menerbitkan dengan row_version", async () => {
    // Setelah terbit, GET /work-plans/p1 mengembalikan SK terbit (detail dimuat ulang setelah transisi).
    let current = plan();
    const calls = detail(plan(), (url) => {
      if (url === "/work-plans/p1/publish") return { data: (current = plan({ status: "PUBLISHED", number: "Rencana Kerja/001" })) };
      if (url === "/work-plans/p1") return { data: current };
    });
    renderRoute("/work-plans/p1", { role: "PM" });
    expect(await screen.findByText("Pasang CCTV 1")).toBeInTheDocument();
    expect(screen.getByText("Instalasi")).toBeInTheDocument();
    for (const name of ["Sunting rencana kerja", "Terbitkan rencana kerja", "Arsipkan draf"]) expect(screen.getByRole("button", { name })).toBeInTheDocument();
    for (const name of ["Sunting draft", "Atur tim", "Tambah hari"]) expect(screen.queryByRole("button", { name })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Terbitkan rencana kerja" }));
    expect(calls.find((c) => c.url === "/work-plans/p1/publish")).toBeUndefined();
    fireEvent.click(await screen.findByRole("button", { name: "Ya, terbitkan" }));
    expect(await screen.findByText("Rencana Kerja/001")).toBeInTheDocument();
    expect(calls.find((c) => c.url === "/work-plans/p1/publish")!.data).toEqual({ row_version: 3, reason: "" });
  });

  it("terbit gagal: dialog tetap terbuka", async () => {
    const calls = detail(plan(), (url) =>
      url === "/work-plans/p1/publish" ? apiError(422, "VALIDATION_ERROR", "Rincian harian belum lengkap.") : undefined,
    );
    renderRoute("/work-plans/p1", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Terbitkan rencana kerja" }));
    fireEvent.click(await screen.findByRole("button", { name: "Ya, terbitkan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/publish")).toBe(true));
    await waitFor(() => expect(screen.getByRole("button", { name: "Ya, terbitkan" })).toBeEnabled());
    expect(screen.getByRole("dialog", { name: "Terbitkan rencana kerja?" })).toBeInTheDocument();
  });

  it("Rencana Kerja terbit: PM tidak punya tombol ketua; menunggu ketua di HP", async () => {
    detail(plan({ status: "PUBLISHED", number: "Rencana Kerja/001" }));
    renderRoute("/work-plans/p1", { role: "PM" });
    await screen.findByText("Rencana Kerja/001");
    expect(screen.getByText(/Notifikasi sudah dikirim ke ketua tim dan anggota/)).toBeInTheDocument();
    for (const name of ["Terima rencana kerja", "Ajukan banding", "Mulai pelaksanaan"]) expect(screen.queryByRole("button", { name })).toBeNull();
  });

  it("revisi diminta: alasan ketua tampil dan PM membuka revisi", async () => {
    const calls = detail(plan({ status: "APPEALED", number: "Rencana Kerja/001", appeal_reason: "Tambah 1 hari" }), (url) =>
      url === "/work-plans/p1/revise" ? { data: plan({ status: "DRAFT", number: "Rencana Kerja/001", revision: 2 }) } : undefined,
    );
    renderRoute("/work-plans/p1", { role: "PM" });
    expect(await screen.findByText(/Ketua tim meminta revisi: "Tambah 1 hari"/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Buka revisi" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/revise")).toBe(true));
    // Draf revisi tidak bisa diarsip, tetapi bisa dibatalkan.
    expect(await screen.findByRole("button", { name: "Batalkan pekerjaan" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Arsipkan draf" })).toBeNull();
  });

  it("karyawan tanpa create:plan tidak melihat tindakan PM", async () => {
    detail(plan());
    renderRoute("/work-plans/p1", { role: "field" });
    await screen.findByText("Pasang CCTV 1");
    expect(screen.queryByRole("button", { name: "Terbitkan rencana kerja" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Sunting rencana kerja" })).toBeNull();
  });

  it("Rencana Kerja tidak ditemukan menampilkan galat", async () => {
    mockApi(() => undefined);
    renderRoute("/work-plans/zz", { role: "PM" });
    expect(await screen.findByText("Work plan tidak ditemukan atau Anda tidak berwenang melihatnya.")).toBeInTheDocument();
  });
});
