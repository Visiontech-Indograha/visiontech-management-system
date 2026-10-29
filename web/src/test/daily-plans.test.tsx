import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

/** Jadwal harian daily-first (M5): kalender bulanan, klik tanggal → detail / buat jadwal, setujui, setujui minggu. */
const todayIso = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
// Nama tombol tanggal di kalender: "<hari, tanggal bulan>: <n> jadwal" atau ": kosong".
const dayLabel = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" })
  .format(new Date(`${todayIso}T00:00:00Z`));
const options = {
  divisions: [{ division_id: "d1", name: "Sipil" }],
  teams: [
    { team_id: "t1", name: "Tim Alpha", division_id: "d1", leader_employee_id: "e-lead", leader_name: "Agus" },
    { team_id: "t2", name: "Tim Bravo", division_id: "d1", leader_employee_id: "e-x", leader_name: "Riko" },
  ],
  orders: [],
};
const plan = (over: Record<string, unknown> = {}) => ({
  daily_plan_id: "p1", division_id: "d1", division_name: "Sipil", team_id: "t1", team_name: "Tim Alpha",
  leader_employee_id: "e-lead", leader_name: "Agus", work_date: todayIso, site_name: "Gardu Induk Minas",
  site_lat: "1.4700000", site_lng: "101.4500000", attendance_radius_m: 150, clock_in_time: "07:00:00",
  clock_out_time: "16:00:00", status: "SUBMITTED", created_by_id: "e-pm", item_count: 2, done_count: 0, can_manage: true, ...over,
});

describe("Jadwal harian", () => {
  it("PM melihat matriks minggu dan menyetujui jadwal yang menunggu", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan()] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan(), items: [], attachment_file_ids: [] } };
      if (c.url === "/work-plans/daily/p1/approve") return { data: plan({ status: "APPROVED" }) };
    });
    renderRoute("/work-plans", { role: "PM" });
    // Satu jadwal di tanggal itu: jendela hari (PM) → baris tim → detail lengkap.
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: 1 jadwal` }));
fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Tim Alpha/ }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Setujui jadwal" }));
    // Aksi penting meminta konfirmasi dulu; belum ada permintaan sebelum dikonfirmasi.
    const confirm = await screen.findByRole("dialog", { name: "Setujui jadwal?" });
    expect(calls.some((c) => c.url === "/work-plans/daily/p1/approve")).toBe(false);
    fireEvent.click(within(confirm).getByRole("button", { name: "Setujui jadwal" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/work-plans/daily/p1/approve")).toBe(true));
  });

  it("setujui minggu ini mengirim semua jadwal yang menunggu", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan(), plan({ daily_plan_id: "p2", team_id: "t2", team_name: "Tim Bravo" })] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/approve") return { data: { approved: ["p1", "p2"], skipped: [] } };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Setujui minggu ini (2)" }));
    await waitFor(() =>
      expect(calls.find((c) => c.url === "/work-plans/daily/approve")?.data).toEqual({ daily_plan_ids: ["p1", "p2"] }),
    );
  });

  it("tanggal kosong membuka form buat jadwal untuk tim & tanggal itu", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/daily") return { data: [] };
      if (c.url === "/work-plans/form-options") return { data: options };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: kosong` }));
    const day = await screen.findByRole("dialog");
    fireEvent.click(within(day).getByRole("button", { name: /Tim Bravo/ }));
    const dialog = await screen.findByRole("dialog", { name: "Buat jadwal harian" });
    expect(within(dialog).getByLabelText("Tim")).toHaveValue("t2");
    expect(within(dialog).getByLabelText("Tanggal")).toHaveValue(todayIso);
    // Lokasi dipilih lewat peta (cari alamat / klik peta), bukan mengetik koordinat sendirian.
    expect(within(dialog).getByLabelText("Cari alamat atau nama tempat")).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Cari koordinat" })).toBeNull();
  });

  it("form buat jadwal menawarkan lokasi terakhir tim dan mengisi koordinat saat dipilih", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily") return { data: [] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/recent-sites") {
        return { data: [
          { site_name: "Gardu Induk Minas", site_lat: "1.4700000", site_lng: "101.4500000", attendance_radius_m: 250, last_used: todayIso },
          { site_name: "Menara Duri", site_lat: "1.2300000", site_lng: "101.1100000", attendance_radius_m: null, last_used: todayIso },
        ] };
      }
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: kosong` }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Tim Bravo/ }));
    const dialog = await screen.findByRole("dialog", { name: "Buat jadwal harian" });
    const chips = await within(dialog).findByTestId("recent-sites");
    expect(calls.some((c) => c.url === "/work-plans/daily/recent-sites" && (c.params as { team_id?: string } | undefined)?.team_id === "t2")).toBe(true);
    fireEvent.click(within(chips).getByRole("button", { name: "Gardu Induk Minas" }));
    expect(within(dialog).getByLabelText("Lokasi site (opsional)")).toHaveValue("Gardu Induk Minas");
    expect(within(dialog).getByLabelText("Lintang (lat)")).toHaveValue("1.4700000");
    expect(within(dialog).getByLabelText("Bujur (lng)")).toHaveValue("101.4500000");
    expect(within(dialog).getByLabelText("Radius absen (m)")).toHaveValue("250");
  });

  it("pekerja lapangan tidak melihat tombol buat/persetujuan", async () => {
    mockApi((c) => (c.url === "/work-plans/daily" ? { data: [plan({ status: "APPROVED" })] } : undefined));
    renderRoute("/work-plans", { role: "field" });
    expect(await screen.findByRole("button", { name: `${dayLabel}: 1 jadwal` })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Buat jadwal/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Setujui minggu ini/ })).toBeNull();
  });
});

describe("F10 · buat jadwal dari sel hari, tanggal lampau, dan hapus", () => {
  const yIso = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date(Date.now() - 86_400_000));
  const yLabel = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" })
    .format(new Date(`${yIso}T00:00:00Z`));

  it("PM membuka sel hari berjadwal lalu melihat tim lain yang belum punya jadwal dengan 'Buat jadwal'", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan()] };
      if (c.url === "/work-plans/form-options") return { data: options };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: 1 jadwal` }));
    const day = await screen.findByRole("dialog");
    expect(within(day).getByRole("button", { name: /Tim Alpha/ })).toBeInTheDocument();
    fireEvent.click(within(day).getByRole("button", { name: /Tim Bravo/ }));
    const form = await screen.findByRole("dialog", { name: "Buat jadwal harian" });
    expect(within(form).getByLabelText("Tim")).toHaveValue("t2");
    expect(within(form).queryByLabelText(/Alasan tanggal lampau/)).toBeNull();
  });

  it("tanggal lampau: buat jadwal meminta alasan dan mengirimnya sebagai backdate_reason", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily" && c.method === "post") return { data: plan({ status: "DRAFT", work_date: yIso }) };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${yLabel}: kosong` }));
    const day = await screen.findByRole("dialog");
    fireEvent.click(within(day).getByRole("button", { name: /Tim Alpha/ }));
    const form = await screen.findByRole("dialog", { name: "Buat jadwal harian" });
    expect(within(form).getByLabelText("Tanggal")).toHaveValue(yIso);
    const submitForm = () => fireEvent.submit(form.querySelector("form") as HTMLFormElement);
    submitForm();
    expect(await within(form).findByText("Isi alasan untuk tanggal lampau.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post" && c.url === "/work-plans/daily")).toBe(false);
    fireEvent.change(within(form).getByLabelText(/Alasan tanggal lampau/), { target: { value: "Hujan, pekerjaan tertunda" } });
    submitForm();
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/work-plans/daily")).toBe(true));
    const body = calls.find((c) => c.method === "post" && c.url === "/work-plans/daily")?.data as Record<string, unknown>;
    expect(body.work_date).toBe(yIso);
    expect(body.backdate_reason).toBe("Hujan, pekerjaan tertunda");
  });

  it("jadwal disetujui yang belum dimulai bisa dihapus setelah konfirmasi", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily/p1" && c.method === "delete") return { status: 204, data: null };
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan({ status: "APPROVED" })] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan({ status: "APPROVED" }), items: [], attachment_file_ids: [] } };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: 1 jadwal` }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Tim Alpha/ }));
    const detail = await screen.findByRole("dialog");
    fireEvent.click(within(detail).getByRole("button", { name: "Hapus" }));
    const confirm = await screen.findByRole("dialog", { name: "Hapus jadwal?" });
    expect(calls.some((c) => c.method === "delete")).toBe(false);
    fireEvent.click(within(confirm).getByRole("button", { name: "Hapus" }));
    await waitFor(() => expect(calls.some((c) => c.method === "delete" && c.url === "/work-plans/daily/p1")).toBe(true));
  });

  it("koordinat diisi tanpa nama lokasi: form menolak dan meminta nama sebelum menyimpan", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily" && c.method === "post") return { data: plan({ status: "DRAFT" }) };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: kosong` }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Tim Bravo/ }));
    const form = await screen.findByRole("dialog", { name: "Buat jadwal harian" });
    fireEvent.change(within(form).getByLabelText("Lintang (lat)"), { target: { value: "0.4213" } });
    fireEvent.change(within(form).getByLabelText("Bujur (lng)"), { target: { value: "101.3806" } });
    fireEvent.submit(form.querySelector("form") as HTMLFormElement);
    expect(await within(form).findByText("Isi nama lokasi bila koordinat diisi (mis. Gudang Cikarang).")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post" && c.url === "/work-plans/daily")).toBe(false);
    fireEvent.change(within(form).getByLabelText("Lokasi site (opsional)"), { target: { value: "Gudang Pekanbaru" } });
    fireEvent.submit(form.querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/work-plans/daily")).toBe(true));
    expect(calls.find((c) => c.method === "post" && c.url === "/work-plans/daily")!.data).toMatchObject({ site_name: "Gudang Pekanbaru", site_lat: 0.4213, site_lng: 101.3806 });
  });

  it("hapus massal: hanya jadwal yang belum dimulai bisa dipilih, konfirmasi, lalu hasil dirangkum", async () => {
    const deleted: string[] = [];
    const calls = mockApi((c) => {
      if (c.method === "delete" && c.url?.startsWith("/work-plans/daily/")) {
        if (c.url === "/work-plans/daily/p2") throw Object.assign(new Error("Jadwal sudah dimulai."), {});
        deleted.push(c.url);
        return { status: 204, data: null };
      }
      if (c.url === "/work-plans/daily" && c.method === "get") {
        return { data: [plan({ status: "APPROVED" }), plan({ daily_plan_id: "p2", team_id: "t2", team_name: "Tim Bravo", status: "DRAFT" }), plan({ daily_plan_id: "p3", team_id: "t3", team_name: "Tim Charlie", status: "ONGOING" })] };
      }
      if (c.url === "/work-plans/form-options") return { data: { ...options, teams: [...options.teams, { team_id: "t3", name: "Tim Charlie", division_id: "d1", leader_employee_id: "e-y", leader_name: "Dian" }] } };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: 3 jadwal` }));
    const day = await screen.findByRole("dialog");
    expect(within(day).queryByRole("checkbox", { name: "Pilih jadwal Tim Charlie" })).toBeNull();
    fireEvent.click(within(day).getByRole("checkbox", { name: "Pilih jadwal Tim Alpha" }));
    fireEvent.click(within(day).getByRole("checkbox", { name: "Pilih jadwal Tim Bravo" }));
    fireEvent.click(within(day).getByRole("button", { name: "Hapus terpilih (2)" }));
    const confirm = await screen.findByRole("dialog", { name: "Hapus jadwal terpilih?" });
    expect(deleted).toEqual([]);
    fireEvent.click(within(confirm).getByRole("button", { name: "Hapus" }));
    await waitFor(() => expect(deleted.length).toBe(1));
    expect(calls.filter((c) => c.method === "delete").map((c) => c.url)).toEqual(["/work-plans/daily/p1", "/work-plans/daily/p2"]);
  });

  it("PM mengubah lokasi jadwal yang disetujui sebelum hari kerjanya, tanpa kembali ke draf", async () => {
    const tomorrow = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date(Date.now() + 86_400_000));
    const tLabel = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" })
      .format(new Date(`${tomorrow}T00:00:00Z`));
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan({ status: "APPROVED", work_date: tomorrow })] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/p1/location") return { data: plan({ status: "APPROVED", work_date: tomorrow, site_name: "Lokasi HP Uji" }) };
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan({ status: "APPROVED", work_date: tomorrow }), items: [], attachment_file_ids: [] } };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${tLabel}: 1 jadwal` }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Tim Alpha/ }));
    const detail = await screen.findByRole("dialog");
    fireEvent.click(within(detail).getByRole("button", { name: "Ubah lokasi" }));
    const form = within(await screen.findByRole("form", { name: "Ubah lokasi jadwal" }));
    fireEvent.change(form.getByLabelText("Nama lokasi"), { target: { value: "Lokasi HP Uji" } });
    fireEvent.change(form.getByLabelText("Lintang (lat)"), { target: { value: "0.4212983" } });
    fireEvent.change(form.getByLabelText("Bujur (lng)"), { target: { value: "101.3806115" } });
    fireEvent.click(form.getByRole("button", { name: "Simpan lokasi" }));
    await waitFor(() => expect(calls.some((c) => c.method === "patch" && c.url === "/work-plans/daily/p1/location")).toBe(true));
    expect(calls.find((c) => c.method === "patch")!.data).toEqual({ site_name: "Lokasi HP Uji", site_lat: 0.4212983, site_lng: 101.3806115, attendance_radius_m: 150 });
    expect(calls.some((c) => c.method === "post" && c.url.endsWith("/submit"))).toBe(false);
  });

  it("jadwal disetujui hari ini tidak menawarkan Ubah lokasi", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan({ status: "APPROVED" })] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan({ status: "APPROVED" }), items: [], attachment_file_ids: [] } };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: 1 jadwal` }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Tim Alpha/ }));
    const detail = await screen.findByRole("dialog");
    expect(within(detail).queryByRole("button", { name: "Ubah lokasi" })).toBeNull();
  });
});
