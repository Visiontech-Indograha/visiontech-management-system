import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { visibleNav } from "@/app/navigation";
import { cellKind, datesBetween, longDate, standbyGroups, summarizeBulk, validateRange, copyWeekTargets, type WeeklyMatrix } from "@/lib/alokasi";
import { addDays, wibDate, weekStart } from "@/services/dailyPlanService";
import { mockApi, renderRoute } from "./utils";

/** Alokasi mingguan (PM/OM): matriks tim × hari, dialog Alokasikan, siaga, ubah SIAGA, salin minggu. */
const todayIso = wibDate();
const nextWeek = addDays(weekStart(todayIso), 7);

const teams = [
  { team_id: "t1", team_name: "Tim Alpha", division_id: "d1", division_name: "Sipil", leader_name: "Agus" },
  { team_id: "t2", team_name: "Tim Bravo", division_id: "d1", division_name: "Sipil", leader_name: "Riko" },
];
const options = {
  divisions: [{ division_id: "d1", name: "Sipil" }, { division_id: "d2", name: "Listrik" }],
  teams: [
    { team_id: "t1", name: "Tim Alpha", division_id: "d1", leader_employee_id: "e1", leader_name: "Agus" },
    { team_id: "t2", name: "Tim Bravo", division_id: "d1", leader_employee_id: "e2", leader_name: "Riko" },
  ],
  orders: [
    { completion_id: "c1", client_name: "PLN", project_title: "Gardu Minas", order_number: "SPK-1", division_id: "d1" },
    { completion_id: "c9", client_name: "Lain", project_title: "Di divisi lain", order_number: null, division_id: "d2" },
  ],
};
const workTypes = [
  { id: "w1", name: "Instalasi Gardu", kind: "INSTALLATION", division_id: "d1", is_active: true },
  { id: "w2", name: "Titik Survei", kind: "SURVEY_POINT", division_id: "d1", is_active: true },
];

/** Matriks untuk minggu yang diminta; `plans` menimpa sel tertentu ("team|tanggal"). */
function matrixFor(weekStartIso: string, plans: Record<string, Record<string, unknown>> = {}, divisions = options.divisions.slice(0, 1)): WeeklyMatrix {
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStartIso, i));
  return {
    week_start: weekStartIso,
    week_end: days[6]!,
    days,
    divisions: divisions.map((d) => ({ division_id: d.division_id, name: d.name })),
    rows: teams.map((t) => ({
      team_id: t.team_id,
      team_name: t.team_name,
      division_id: t.division_id,
      division_name: t.division_name,
      leader_name: t.leader_name,
      cells: days.map((d) => ({
        work_date: d,
        daily_plan_id: null,
        status: null,
        kind: null,
        item_count: 0,
        items: [],
        orders: [],
        ...(plans[`${t.team_id}|${d}`] ?? {}),
      })),
    })),
  } as unknown as WeeklyMatrix;
}

const cellName = (team: string, date: string, label: string) => `${team}, ${longDate(date)}: ${label}`;

describe("Alokasi mingguan — peran dan navigasi", () => {
  it("menu hanya untuk PM/OM (izin create:plan); ketua lapangan dan HR tidak melihatnya", () => {
    const labels = (perms: string[]) => visibleNav(perms).map((i) => i.label);
    expect(labels(["create:plan"])).toContain("Alokasi mingguan");
    expect(labels(["view:users", "upload:documents", "view:documents"])).not.toContain("Alokasi mingguan");
    expect(labels(["manage:users", "verify:documents"])).not.toContain("Alokasi mingguan");
  });

  it("PM tidak melihat tombol 'Ajukan ke PM' di halaman ini", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/weekly") return { data: matrixFor(weekStart(todayIso)) };
      if (c.url === "/work-plans/form-options") return { data: options };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    await screen.findByRole("table", { name: "Matriks alokasi mingguan" });
    expect(screen.queryByRole("button", { name: /Ajukan ke PM/ })).toBeNull();
  });
});

describe("Alokasi mingguan — matriks dan legenda", () => {
  it("menampilkan tim × 7 hari dengan label status dan legenda", async () => {
    const mon = weekStart(todayIso);
    mockApi((c) => {
      if (c.url === "/work-plans/weekly") {
        return {
          data: matrixFor(mon, {
            [`t1|${addDays(mon, 1)}`]: { daily_plan_id: "p1", status: "SUBMITTED", kind: "WORK", item_count: 2 },
            [`t2|${addDays(mon, 2)}`]: { daily_plan_id: "p2", status: "APPROVED", kind: "STANDBY" },
          }),
        };
      }
      if (c.url === "/work-plans/form-options") return { data: options };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    const table = await screen.findByRole("table", { name: "Matriks alokasi mingguan" });
    expect(within(table).getAllByRole("columnheader")).toHaveLength(8);
    expect(screen.getByRole("button", { name: cellName("Tim Alpha", addDays(mon, 1), "Diajukan") + ", 2 item" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: cellName("Tim Bravo", addDays(mon, 2), "SIAGA") })).toBeInTheDocument();
    const legend = screen.getByRole("list", { name: "Keterangan warna sel" });
    for (const label of ["Kosong", "Draf", "Diajukan", "Disetujui", "Berjalan", "Selesai", "SIAGA"]) {
      expect(within(legend).getByText(label)).toBeInTheDocument();
    }
  });

  it("navigasi minggu meminta week_start minggu berikutnya dan kembali ke minggu ini", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/weekly") {
        const ws = String((c.params as { week_start: string }).week_start);
        return { data: matrixFor(ws) };
      }
      if (c.url === "/work-plans/form-options") return { data: options };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    await screen.findByRole("table", { name: "Matriks alokasi mingguan" });
    fireEvent.click(screen.getByRole("button", { name: "Minggu berikutnya" }));
    await waitFor(() => expect(calls.some((c) => (c.params as { week_start?: string })?.week_start === nextWeek)).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: "Hari ini" }));
    await waitFor(() =>
      expect(calls.filter((c) => c.url === "/work-plans/weekly").slice(-1)[0]?.params).toMatchObject({ week_start: weekStart(todayIso) }),
    );
  });

  it("pemilih divisi tampil bila PM memegang dua divisi dan default 'Semua divisi'", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/weekly") return { data: matrixFor(weekStart(todayIso)) };
      if (c.url === "/work-plans/form-options") return { data: options };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    await screen.findByRole("table", { name: "Matriks alokasi mingguan" });
    const picker = screen.getByLabelText("Divisi");
    expect(picker).toHaveValue("");
    fireEvent.change(picker, { target: { value: "d2" } });
    await waitFor(() => expect(calls.some((c) => (c.params as { division_id?: string })?.division_id === "d2")).toBe(true));
  });

  it("status loading dan error ditampilkan dengan teks Bahasa Indonesia", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/weekly") return { status: 500, data: { error: { code: "X", message: "Gagal", details: {} } } };
      if (c.url === "/work-plans/form-options") return { data: options };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    expect(await screen.findByText(/Alokasi mingguan belum dapat dimuat/)).toBeInTheDocument();
  });
});

describe("Alokasi mingguan — dialog Alokasikan", () => {
  it("T-3: menjelaskan syarat order dan tanpa teks teknis API", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/weekly") return { data: matrixFor(String((c.params as { week_start: string }).week_start)) };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-types") return { data: workTypes };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    await screen.findByRole("table", { name: "Matriks alokasi mingguan" });
    fireEvent.click(screen.getByRole("button", { name: "Minggu berikutnya" }));
    fireEvent.click(await screen.findByRole("button", { name: cellName("Tim Alpha", addDays(nextWeek, 1), "Kosong") }));
    const dialog = await screen.findByRole("dialog", { name: "Alokasikan" });
    expect(within(dialog).getByText(/Hanya order yang surveinya sudah disetujui yang bisa dialokasikan/)).toBeInTheDocument();
    expect(within(dialog).queryByText(/belum tersedia di API/)).toBeNull();
  });

  it("klik sel kosong membuka dialog; kirim bulk lalu tambah item dan tampilkan hasil per sel", async () => {
    const day = addDays(nextWeek, 1);
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/weekly") {
        const ws = String((c.params as { week_start: string }).week_start);
        return { data: matrixFor(ws === nextWeek ? nextWeek : ws) };
      }
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-types") return { data: workTypes };
      if (c.url === "/work-plans/orders/c1/schedule")
        return { data: { total_target_unit: 10, completed_target_unit: 2, scheduled_target_qty: 3, unscheduled_target_qty: 5, plans: [] } };
      if (c.url === "/work-plans/daily/bulk")
        return {
          data: {
            created: 1,
            skipped: 1,
            cells: [
              { team_id: "t1", work_date: day, status: "CREATED", daily_plan_id: "new1", warnings: [{ code: "LEADER_CUTI", message: "Ketua tim sedang cuti pada tanggal ini." }] },
              { team_id: "t2", work_date: day, status: "SKIPPED", reason: "TEAM_DAY_TAKEN", message: "Tim sudah punya jadwal.", warnings: [] },
            ],
          },
        };
      if (c.url === "/work-plans/daily/new1/items") return { status: 201, data: { item_id: "i1" } };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    await screen.findByRole("table", { name: "Matriks alokasi mingguan" });
    fireEvent.click(screen.getByRole("button", { name: "Minggu berikutnya" }));
    fireEvent.click(await screen.findByRole("button", { name: cellName("Tim Alpha", day, "Kosong") }));

    const dialog = await screen.findByRole("dialog", { name: "Alokasikan" });
    // Validasi: order belum dipilih.
    fireEvent.click(within(dialog).getByRole("button", { name: "Alokasikan" }));
    expect(await within(dialog).findByText("Pilih order klien.")).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/work-plans/daily/bulk")).toBe(false);

    fireEvent.change(within(dialog).getByLabelText("Order klien"), { target: { value: "c1" } });
    await waitFor(() => expect(within(dialog).getByRole("status").textContent).toMatch(/belum dijadwalkan: 5 dari/));
    fireEvent.change(within(dialog).getByLabelText("Jenis pekerjaan (template)"), { target: { value: "w1" } });
    fireEvent.change(within(dialog).getByLabelText("Judul pekerjaan"), { target: { value: "Pasang gardu" } });
    fireEvent.click(within(dialog).getByRole("checkbox", { name: "Tim Bravo" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Alokasikan" }));

    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/daily/bulk")).toBe(true));
    const bulk = calls.find((c) => c.url === "/work-plans/daily/bulk")!;
    expect(bulk.data).toMatchObject({ division_id: "d1", team_ids: ["t1", "t2"], kind: "WORK", target: "DRAFT", work_dates: [day] });
    const item = calls.find((c) => c.url === "/work-plans/daily/new1/items")!;
    expect(item.data).toMatchObject({ work_type_id: "w1", title: "Pasang gardu", completion_id: "c1", target_qty: 1 });

    const result = await screen.findByText("Hasil alokasi");
    const panel = result.parentElement as HTMLElement;
    expect(within(panel).getByText(/1 jadwal dibuat, 1 dilewati/)).toBeInTheDocument();
    expect(within(panel).getByText(/Peringatan cuti ketua/)).toBeInTheDocument();
  });

  it("perubahan belum disimpan meminta konfirmasi sebelum dialog ditutup", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/weekly") return { data: matrixFor(nextWeek) };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-types") return { data: workTypes };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    await screen.findByRole("table", { name: "Matriks alokasi mingguan" });
    fireEvent.click(screen.getByRole("button", { name: "Minggu berikutnya" }));
    fireEvent.click(await screen.findByRole("button", { name: cellName("Tim Alpha", addDays(nextWeek, 2), "Kosong") }));
    const dialog = await screen.findByRole("dialog", { name: "Alokasikan" });
    fireEvent.change(within(dialog).getByLabelText("Judul pekerjaan"), { target: { value: "Coba" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Batal" }));
    expect(await screen.findByText("Perubahan belum disimpan. Tutup tanpa menyimpan?")).toBeInTheDocument();
  });

  it("sel SIAGA memberi aksi 'Ubah jadi pekerjaan' yang mengirim activate dengan item", async () => {
    const day = addDays(nextWeek, 3);
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/weekly") {
        return { data: matrixFor(nextWeek, { [`t1|${day}`]: { daily_plan_id: "s1", status: "APPROVED", kind: "STANDBY" } }) };
      }
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-types") return { data: workTypes };
      if (c.url === "/work-plans/orders/c1/schedule")
        return { data: { total_target_unit: 4, completed_target_unit: 0, scheduled_target_qty: 0, unscheduled_target_qty: 4, plans: [] } };
      if (c.url === "/work-plans/daily/s1/activate") return { data: { daily_plan_id: "s1", kind: "WORK" } };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    await screen.findByRole("table", { name: "Matriks alokasi mingguan" });
    fireEvent.click(screen.getByRole("button", { name: "Minggu berikutnya" }));
    fireEvent.click(await screen.findByRole("button", { name: cellName("Tim Alpha", day, "SIAGA") }));
    const dialog = await screen.findByRole("dialog", { name: "Ubah SIAGA jadi pekerjaan" });
    fireEvent.change(within(dialog).getByLabelText("Order klien"), { target: { value: "c1" } });
    fireEvent.change(within(dialog).getByLabelText("Jenis pekerjaan (template)"), { target: { value: "w1" } });
    fireEvent.change(within(dialog).getByLabelText("Judul pekerjaan"), { target: { value: "Ganti trafo" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ubah jadi pekerjaan" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/daily/s1/activate")).toBe(true));
    const act = calls.find((c) => c.url === "/work-plans/daily/s1/activate")!;
    expect(act.data).toMatchObject({ items: [{ work_type_id: "w1", title: "Ganti trafo", completion_id: "c1" }] });
  });
});

describe("Alokasi mingguan — siaga dan salin minggu", () => {
  it("'Siaga hari kosong' mengirim bulk-standby hanya untuk tim dan tanggal yang kosong", async () => {
    const day = addDays(nextWeek, 1);
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/weekly") {
        return { data: matrixFor(nextWeek, { [`t1|${day}`]: { daily_plan_id: "p1", status: "APPROVED", kind: "WORK" } }) };
      }
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/bulk-standby")
        return { data: { created: 13, skipped: 1, cells: [] } };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    await screen.findByRole("table", { name: "Matriks alokasi mingguan" });
    fireEvent.click(screen.getByRole("button", { name: "Minggu berikutnya" }));
    fireEvent.click(await screen.findByRole("button", { name: /Siaga hari kosong \(13\)/ }));
    const dialog = await screen.findByRole("dialog", { name: "Siaga hari kosong?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Buat siaga" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/daily/bulk-standby")).toBe(true));
    const body = calls.find((c) => c.url === "/work-plans/daily/bulk-standby")!.data as { team_ids: string[]; work_dates: string[] };
    expect(body.team_ids).toEqual(["t1", "t2"]);
    expect(body.work_dates).toHaveLength(7);
  });

  it("'Salin minggu' menyalin tiap jadwal ke +7 hari lewat endpoint copy", async () => {
    const mon = weekStart(todayIso);
    const day = addDays(mon, 1);
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/weekly") return { data: matrixFor(mon, { [`t1|${day}`]: { daily_plan_id: "p1", status: "DRAFT", kind: "WORK" } }) };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/p1/copy") return { data: [] };
    });
    renderRoute("/alokasi-mingguan", { role: "PM" });
    await screen.findByRole("table", { name: "Matriks alokasi mingguan" });
    fireEvent.click(screen.getByRole("button", { name: "Salin minggu ke minggu berikutnya" }));
    const dialog = await screen.findByRole("dialog", { name: "Salin minggu ke minggu berikutnya?" });
    expect(within(dialog).getByText(/1 jadwal minggu ini disalin/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Salin" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/daily/p1/copy")).toBe(true));
    expect(calls.find((c) => c.url === "/work-plans/daily/p1/copy")!.data).toEqual({ work_dates: [addDays(day, 7)] });
  });
});

describe("Alokasi mingguan — fungsi murni", () => {
  it("kategori sel: SIAGA mengalahkan status; sel tanpa jadwal = EMPTY", () => {
    expect(cellKind({ work_date: "2026-11-02", daily_plan_id: null } as never)).toBe("EMPTY");
    expect(cellKind({ work_date: "2026-11-02", daily_plan_id: "x", kind: "STANDBY", status: "DRAFT" } as never)).toBe("STANDBY");
    expect(cellKind({ work_date: "2026-11-02", daily_plan_id: "x", kind: "WORK", status: "ONGOING" } as never)).toBe("ONGOING");
  });

  it("rentang tanggal: hanya hari kerja bila diminta; batas 31 hari dan urutan tanggal", () => {
    expect(datesBetween("2026-11-02", "2026-11-08", true)).toEqual(["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]);
    expect(datesBetween("2026-11-02", "2026-11-08", false)).toHaveLength(7);
    expect(validateRange("2026-11-08", "2026-11-02")).toMatch(/setelah tanggal mulai/);
    expect(validateRange("2026-11-01", "2026-12-15")).toMatch(/maksimal 31/);
    expect(validateRange("2026-11-01", "2026-11-03")).toBeNull();
  });

  it("siaga per divisi hanya memuat sel kosong masa depan", () => {
    const mon = "2026-11-02";
    const m = matrixFor(mon, { "t1|2026-11-03": { daily_plan_id: "p" } }, options.divisions);
    const groups = standbyGroups(m, "2026-11-03");
    expect(groups).toHaveLength(1);
    expect(groups[0]!.team_ids).toEqual(["t1", "t2"]);
    expect(groups[0]!.work_dates).not.toContain("2026-11-02");
    expect(groups[0]!.work_dates).toContain("2026-11-03");
  });

  it("salin minggu membidik tanggal +7 untuk tiap jadwal yang ada", () => {
    const m = matrixFor("2026-11-02", { "t1|2026-11-04": { daily_plan_id: "p9" } });
    expect(copyWeekTargets(m)).toEqual([{ daily_plan_id: "p9", work_date: "2026-11-11" }]);
  });

  it("ringkasan hasil bulk menghitung dibuat, dilewati, dan peringatan", () => {
    const s = summarizeBulk({
      created: 1,
      skipped: 1,
      cells: [
        { team_id: "t1", work_date: "2026-11-02", status: "CREATED", warnings: [{ code: "ASET_BENTROK", message: "x" }] },
        { team_id: "t2", work_date: "2026-11-02", status: "SKIPPED", warnings: [] },
      ],
    } as never);
    expect(s).toEqual({ created: 1, skipped: 1, warnings: 1 });
  });
});
