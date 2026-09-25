import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const plan = (over: Record<string, unknown> = {}) => ({
  id: "p1",
  title: "Instalasi CCTV Gudang",
  unit_id: "u1",
  site_id: null,
  location_text: "Cikarang",
  description: null,
  period_start: "2026-10-01",
  period_end: "2026-10-05",
  pm_employee_id: "e-pm",
  leader_employee_id: "e-lead",
  number: null,
  status: "DRAFT",
  revision: 0,
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
const employees = { items: [emp("e-pm", "Pak PM"), emp("e-lead", "Bu Ketua"), emp("e-x", "Tanpa Unit", null)], total: 3, page: 1, size: 100 };

describe("Work plan — daftar", () => {
  it("menampilkan kartu SK dan mengirim filter status", async () => {
    const calls = mockApi((c) => (c.url === "/work-plans" ? { data: [plan()] } : undefined));
    renderRoute("/work-plans", { role: "field" });
    expect(await screen.findByText("Instalasi CCTV Gudang")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Buat SK" })).toBeNull();
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

  it("draft terarsip dipulihkan dari daftar (restore)", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans") return { data: [plan()] };
      if (c.url === "/work-plans/p1/restore") return { data: plan({ row_version: 4 }) };
    });
    renderRoute("/work-plans", { role: "PM" });
    await screen.findByText("Instalasi CCTV Gudang");
    fireEvent.click(screen.getByLabelText("Tampilkan draft terarsip"));
    fireEvent.click(await screen.findByRole("button", { name: "Pulihkan draft" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/restore")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/p1/restore")!.data).toEqual({ row_version: 3, reason: "" });
  });

  it("buat SK memakai unit PM yang dipilih", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans" && c.method === "get") return { data: [] };
      if (c.url === "/employees") return { data: employees };
      if (c.url === "/sites") return { data: [] };
      if (c.url === "/work-plans" && c.method === "post") return { status: 201, data: plan() };
      if (c.url === "/work-plans/p1") return { data: plan() };
    });
    const { router } = renderRoute("/work-plans", { role: "PM" });
    fireEvent.click((await screen.findAllByRole("button", { name: "Buat SK" }))[0]);
    const dialog = screen.getByRole("dialog", { name: "Buat SK" });
    await within(dialog).findAllByRole("option", { name: /Pak PM/ });
    fireEvent.change(within(dialog).getByLabelText("Judul pekerjaan"), { target: { value: "Instalasi CCTV Gudang" } });
    fireEvent.change(within(dialog).getByLabelText("Lokasi"), { target: { value: "Cikarang" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal mulai"), { target: { value: "2026-10-01" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal selesai"), { target: { value: "2026-10-05" } });
    fireEvent.change(within(dialog).getByLabelText("PM pekerjaan"), { target: { value: "e-pm" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/work-plans/p1"));
    expect(calls.find((c) => c.method === "post")!.data).toEqual({
      title: "Instalasi CCTV Gudang",
      location_text: "Cikarang",
      description: null,
      period_start: "2026-10-01",
      period_end: "2026-10-05",
      pm_employee_id: "e-pm",
      leader_employee_id: null,
      site_id: null,
      unit_id: "u1",
    });
  });

  it("validasi: tanggal selesai sebelum mulai dan PM tanpa unit", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans") return { data: [] };
      if (c.url === "/employees") return { data: employees };
      if (c.url === "/sites") return { data: [] };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click((await screen.findAllByRole("button", { name: "Buat SK" }))[0]);
    const dialog = screen.getByRole("dialog", { name: "Buat SK" });
    await within(dialog).findAllByRole("option", { name: /Tanpa Unit/ });
    fireEvent.change(within(dialog).getByLabelText("Judul pekerjaan"), { target: { value: "X" } });
    fireEvent.change(within(dialog).getByLabelText("Lokasi"), { target: { value: "Y" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal mulai"), { target: { value: "2026-10-05" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal selesai"), { target: { value: "2026-10-01" } });
    fireEvent.change(within(dialog).getByLabelText("PM pekerjaan"), { target: { value: "e-x" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByText("Tanggal selesai tidak boleh sebelum tanggal mulai.")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Tanggal selesai"), { target: { value: "2026-10-06" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByText("Karyawan ini belum terdaftar di unit bisnis mana pun.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post")).toBe(false);
  });
});

describe("Work plan — detail & tindakan", () => {
  const detail = (p: ReturnType<typeof plan>, extra?: (url: string, method: string) => { status?: number; data?: unknown } | undefined) =>
    mockApi((c) => {
      const hit = extra?.(c.url ?? "", c.method ?? "get");
      if (hit) return hit;
      if (c.url === "/work-plans/p1") return { data: p };
      if (c.url === "/employees") return { data: employees };
    });

  it("PM melihat tindakan draft dan menerbitkan dengan row_version", async () => {
    const calls = detail(plan(), (url) => (url === "/work-plans/p1/publish" ? { data: plan({ status: "PUBLISHED", number: "SK/001" }) } : undefined));
    renderRoute("/work-plans/p1", { role: "PM" });
    expect(await screen.findByText("Bu Ketua")).toBeInTheDocument();
    for (const name of ["Sunting draft", "Atur tim", "Tambah hari", "Arsipkan draft"])
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Terbitkan SK" }));
    expect(await screen.findByText("SK/001")).toBeInTheDocument();
    expect(calls.find((c) => c.url === "/work-plans/p1/publish")!.data).toEqual({ row_version: 3, reason: "" });
  });

  it("karyawan tanpa create:plan tidak melihat tindakan PM", async () => {
    detail(plan());
    renderRoute("/work-plans/p1", { role: "field" });
    await screen.findByText("Cikarang");
    expect(screen.queryByRole("button", { name: "Terbitkan SK" })).toBeNull();
  });

  it("ketua: banding memerlukan alasan, galat API ditampilkan apa adanya", async () => {
    const calls = detail(plan({ status: "PUBLISHED" }), (url) =>
      url === "/work-plans/p1/appeal"
        ? apiError(403, "FORBIDDEN", "Hanya ketua tim menurut SK yang berlaku yang dapat melakukan tindakan ini.")
        : undefined,
    );
    renderRoute("/work-plans/p1", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Ajukan banding" }));
    const dialog = screen.getByRole("dialog", { name: "Ajukan banding" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajukan banding" }));
    expect(await within(dialog).findByText("Alasan wajib diisi.")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Alasan banding"), { target: { value: "Jadwal bentrok" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajukan banding" }));
    expect(
      await within(dialog).findByText("Hanya ketua tim menurut SK yang berlaku yang dapat melakukan tindakan ini."),
    ).toBeInTheDocument();
    expect(calls.find((c) => c.url === "/work-plans/p1/appeal")!.data).toEqual({ row_version: 3, reason: "Jadwal bentrok" });
  });

  it("tambah hari mengirim POST days lalu PUT plan dengan tugas", async () => {
    const calls = detail(plan(), (url, method) => {
      if (url === "/work-plans/p1/days" && method === "post")
        return { data: { id: "d1", work_plan_id: "p1", work_date: "2026-10-02", title: "Survei", sort_order: 0 } };
      if (url === "/work-plans/p1/days/d1/plan") return { data: { id: "d1", title: "Survei", tasks: ["Ukur"] } };
    });
    renderRoute("/work-plans/p1", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah hari" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah hari" });
    fireEvent.change(within(dialog).getByLabelText("Tanggal"), { target: { value: "2026-10-02" } });
    fireEvent.change(within(dialog).getByLabelText("Judul hari"), { target: { value: "Survei" } });
    fireEvent.change(within(dialog).getByLabelText("Tugas 1"), { target: { value: "Ukur" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/days/d1/plan")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/p1/days")!.data).toEqual({ work_date: "2026-10-02", title: "Survei" });
    expect(calls.find((c) => c.url === "/work-plans/p1/days/d1/plan")!.data).toEqual({ title: "Survei", tasks: [{ title: "Ukur" }] });
  });

  it("atur tim mengirim ketua, anggota tanpa ketua, dan row_version", async () => {
    const calls = detail(plan(), (url) =>
      url === "/work-plans/p1/members" ? { data: { leader_employee_id: "e-lead", member_employee_ids: ["e-pm"], row_version: 4 } } : undefined,
    );
    renderRoute("/work-plans/p1", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Atur tim" }));
    const dialog = screen.getByRole("dialog", { name: "Atur tim" });
    fireEvent.click(await within(dialog).findByLabelText(/Pak PM/));
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/p1/members")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/p1/members")!.data).toEqual({
      leader_employee_id: "e-lead",
      member_employee_ids: ["e-pm"],
      row_version: 3,
    });
  });

  it("SK tidak ditemukan menampilkan galat", async () => {
    mockApi(() => undefined);
    renderRoute("/work-plans/zz", { role: "PM" });
    expect(await screen.findByText("Work plan tidak ditemukan atau Anda tidak berwenang melihatnya.")).toBeInTheDocument();
  });
});
