import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const page = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 25 });

const item = (over: Record<string, unknown> = {}) => ({
  id: "a1",
  user_id: "u1",
  attendance_date: "2026-09-21",
  checked_in_at: "2026-09-21T00:42:00Z", // 07.42 WIB
  latitude: "0.4",
  longitude: "101.9",
  accuracy_m: "12.0",
  distance_to_city_m: "25000.0",
  risk_flags: [],
  source: "MOBILE",
  is_manual: false,
  manual_reason: null,
  note: null,
  device_id: "dev",
  device_model: "Pixel",
  selfie_url: "/api/v1/attendance/a1/selfie",
  map_url: "https://www.google.com/maps?q=0.4,101.9",
  username: "budi",
  full_name: "Budi Santoso",
  role: "user",
  user_type: "WTL",
  employee_no: null,
  ...over,
});

// jsdom tidak menyediakan URL.createObjectURL/revokeObjectURL.
const urlApi = URL as unknown as Record<string, unknown>;
beforeEach(() => {
  urlApi.createObjectURL = () => "blob:selfie-1";
  urlApi.revokeObjectURL = () => {};
});
afterEach(() => {
  delete urlApi.createObjectURL;
  delete urlApi.revokeObjectURL;
});

describe("absensi Finance/SA", () => {
  it("menampilkan daftar, badge tinjauan, dan jam WIB", async () => {
    mockApi((c) =>
      c.url === "/attendance"
        ? { data: page([item(), item({ id: "a2", full_name: "Citra", risk_flags: ["ROOTED"], user_type: "DRIVER" })]) }
        : undefined,
    );
    renderRoute("/attendance", { role: "finance" });
    expect(await screen.findByText("Budi Santoso")).toBeInTheDocument();
    expect(screen.getAllByText("07.42 WIB").length).toBeGreaterThan(0);
    expect(screen.getByText("Normal")).toBeInTheDocument();
    expect(screen.getByText("Perlu ditinjau", { selector: "span" })).toBeInTheDocument();
  });

  it("filter dikirim ke server dan halaman kembali ke 1", async () => {
    const calls = mockApi((c) => (c.url === "/attendance" ? { data: page([]) } : undefined));
    renderRoute("/attendance", { role: "finance" });
    await screen.findByText(/Belum ada absensi/);
    fireEvent.change(screen.getByLabelText("Filter tinjauan"), { target: { value: "true" } });
    await waitFor(() => expect(calls.some((c) => c.url === "/attendance" && calls.length > 1)).toBe(true));
    expect(screen.getByLabelText("Filter tinjauan")).toHaveValue("true");
  });

  it("panel detail: selfie diambil lewat blob berautentikasi, peta, dan flags", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/attendance") return { data: page([item({ risk_flags: ["MOCK_APP_INSTALLED", "DEVICE_CHANGED"] })]) };
      if (c.url === "/attendance/a1/selfie") return { data: new Blob(["x"], { type: "image/jpeg" }) };
    });
    renderRoute("/attendance", { role: "finance" });
    fireEvent.click(await screen.findByRole("button", { name: "Budi Santoso" }));
    const panel = await screen.findByRole("dialog", { name: "Detail absensi" });
    expect(within(panel).getByText("Aplikasi lokasi palsu terpasang")).toBeInTheDocument();
    expect(within(panel).getByText("Perangkat berbeda dari absen sebelumnya")).toBeInTheDocument();
    expect(within(panel).getByRole("link", { name: "Buka peta" })).toHaveAttribute("href", expect.stringContaining("maps?q=0.4,101.9"));
    const img = await within(panel).findByRole("img", { name: "Selfie absen" });
    expect(img).toHaveAttribute("src", "blob:selfie-1");
    expect(calls.some((c) => c.url === "/attendance/a1/selfie")).toBe(true);
    fireEvent.click(within(panel).getByRole("button", { name: "Tutup" }));
    expect(screen.queryByRole("dialog", { name: "Detail absensi" })).toBeNull();
  });

  it("koreksi manual tidak memuat selfie", async () => {
    mockApi((c) =>
      c.url === "/attendance"
        ? { data: page([item({ is_manual: true, source: "MANUAL", selfie_url: null, manual_reason: "Sinyal hilang" })]) }
        : undefined,
    );
    renderRoute("/attendance", { role: "finance" });
    fireEvent.click(await screen.findByRole("button", { name: "Budi Santoso" }));
    const panel = await screen.findByRole("dialog", { name: "Detail absensi" });
    expect(within(panel).getByText("Sinyal hilang")).toBeInTheDocument();
    expect(within(panel).getByText(/Tidak ada selfie/)).toBeInTheDocument();
  });

  it("Finance melihat tombol ekspor tetapi tidak koreksi; ekspor memanggil endpoint", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/attendance") return { data: page([]) };
      if (c.url === "/attendance/export") return { data: new Blob(["x"]) };
    });
    renderRoute("/attendance", { role: "finance" });
    expect(await screen.findByRole("button", { name: "Ekspor XLSX" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Koreksi absen" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Ekspor CSV" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/attendance/export")).toBe(true));
  });

  it("role yang tidak berwenang ditolak", () => {
    mockApi(() => undefined);
    for (const role of ["admin", "hes", "wtl", "driver", "team_leader"]) {
      const { router, unmount } = renderRoute("/attendance", { role });
      expect(router.state.location.pathname).toBe("/forbidden");
      unmount();
    }
  });
});

describe("absensi team dan koreksi", () => {
  it("TL melihat koreksi tetapi bukan ekspor", async () => {
    mockApi((c) => (c.url === "/attendance" ? { data: page([]) } : undefined));
    renderRoute("/attendance/team", { role: "team_leader" });
    expect(await screen.findByRole("button", { name: "Koreksi absen" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ekspor XLSX" })).toBeNull();
  });

  it("koreksi mengirim alasan dan galat server tampil pada field", async () => {
    let n = 0;
    const calls = mockApi((c) => {
      if (c.url === "/attendance" && c.method === "get") return { data: page([]) };
      if (c.url === "/employees")
        return { data: { items: [{ id: "u1", full_name: "Budi Santoso" }], total: 1, page: 1, page_size: 100 } };
      if (c.url === "/attendance/corrections") {
        n += 1;
        return n === 1
          ? apiError(422, "VALIDATION_ERROR", "x", { fields: { manual_reason: "Alasan koreksi wajib diisi." } })
          : { status: 201, data: item({ is_manual: true }) };
      }
    });
    renderRoute("/attendance/team", { role: "team_leader" });
    fireEvent.click(await screen.findByRole("button", { name: "Koreksi absen" }));
    const dialog = screen.getByRole("dialog", { name: "Koreksi absen" });
    await within(dialog).findByRole("option", { name: "Budi Santoso" });
    fireEvent.change(within(dialog).getByLabelText("Karyawan"), { target: { value: "u1" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan koreksi" }));
    expect(await screen.findByText("Alasan koreksi wajib diisi.")).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText("Alasan"), { target: { value: "Sinyal hilang" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan koreksi" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Koreksi absen" })).toBeNull());
    const posts = calls.filter((c) => c.url === "/attendance/corrections");
    expect(posts[1].data).toMatchObject({ user_id: "u1", manual_reason: "Sinyal hilang" });
  });
});

describe("Beranda: ringkasan absensi", () => {
  const policy = (over: Record<string, unknown> = {}) => ({
    open_time: "00:00:00",
    cutoff_time: "08:00:00",
    allow_web: false,
    max_gps_accuracy_m: 100,
    server_time: "2026-09-21T00:30:00Z",
    attendance_date: "2026-09-21",
    timezone: "Asia/Jakarta",
    already_submitted: false,
    window_open: true,
    ...over,
  });

  it("menjelaskan absen lewat Android dan status hari ini (belum absen)", async () => {
    mockApi((c) => {
      if (c.url === "/attendance/policy") return { data: policy() };
      if (c.url === "/attendance/me") return { data: [] };
    });
    renderRoute("/", { role: "wtl" });
    expect(await screen.findByText(/Absen luar kota dilakukan lewat aplikasi Android/)).toBeInTheDocument();
    expect(screen.getByText(/Batas absen pukul 08.00 WIB/)).toBeInTheDocument();
    expect(await screen.findByText("Belum absen hari ini")).toBeInTheDocument();
  });

  it("menampilkan sudah absen dan riwayat", async () => {
    mockApi((c) => {
      if (c.url === "/attendance/policy") return { data: policy({ already_submitted: true }) };
      if (c.url === "/attendance/me") return { data: [item(), item({ id: "a0", attendance_date: "2026-09-20", risk_flags: ["ROOTED"] })] };
    });
    renderRoute("/", { role: "driver" });
    expect(await screen.findByText("Sudah absen")).toBeInTheDocument();
    expect(await screen.findByText("20 Sep 2026")).toBeInTheDocument();
    expect(screen.getAllByText("Perlu ditinjau").length).toBeGreaterThan(0);
  });

  it("jendela ditutup", async () => {
    mockApi((c) => {
      if (c.url === "/attendance/policy") return { data: policy({ window_open: false }) };
      if (c.url === "/attendance/me") return { data: [] };
    });
    renderRoute("/", { role: "finance" });
    expect(await screen.findByText(/jendela absen sudah ditutup/)).toBeInTheDocument();
  });

  it("Super Admin tidak melihat bagian absensi (tidak absen)", () => {
    mockApi(() => undefined);
    renderRoute("/", { role: "super_admin" });
    expect(screen.queryByRole("region", { name: "Absensi" })).toBeNull();
  });
});
