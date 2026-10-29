import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { DailyPlanDetailDialog } from "@/components/organisms/work-plans/DailyPlanDetailDialog";
import type { DailyPlan } from "@/services/dailyPlanService";
import { apiError, mockApi } from "./utils";

/** Temuan uji manual web (pm1): jadwal harian — draf kosong, hapus item, salin ke hari lain. */

const todayIso = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());

const plan = (over: Partial<DailyPlan> = {}): DailyPlan => ({
  daily_plan_id: "p1", division_id: "d1", division_name: "Sipil", team_id: "t1", team_name: "Tim Alpha",
  leader_employee_id: "e-lead", leader_name: "Agus", work_date: todayIso, site_name: "Gardu Induk Minas",
  site_lat: "1.4700000", site_lng: "101.4500000", attendance_radius_m: 150, clock_in_time: "07:00:00",
  clock_out_time: "16:00:00", status: "DRAFT", created_by_id: "e-pm", item_count: 0, done_count: 0, progress_pct: 0, phases: [], ...over,
});

const item = {
  item_id: "i1", task_phase: "INSTALLATION", title: "Titik CCTV 01", status: "TODO", completed_qty: "0",
  target_qty: "1", completion_id: null, depends_on_item_id: null, rollover_approval_status: null,
  location_name: null, site_lat: null, site_lng: null,
};

function renderDialog(props: Partial<{ plan: ReturnType<typeof plan> }> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const p = props.plan ?? plan();
  return render(
    <QueryClientProvider client={client}>
      <DailyPlanDetailDialog plan={p} canPlan isLeader={false} onEdit={() => {}} onClose={() => {}} />
    </QueryClientProvider>,
  );
}

describe("jadwal harian tanpa item", () => {
  it("Ajukan dan Setujui nonaktif dengan petunjuk saat jadwal belum berisi pekerjaan", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan(), items: [], attachment_file_ids: [] } };
    });
    renderDialog();
    expect(await screen.findByRole("button", { name: "Ajukan ke PM" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Setujui jadwal" })).toBeDisabled();
    expect(screen.getByText(/Tambahkan minimal satu pekerjaan/)).toBeInTheDocument();
  });

  it("galat 'belum berisi pekerjaan' hilang setelah item ditambahkan", async () => {
    let itemCount = 1;
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily/p1" && c.method === "get") {
        return { data: { ...plan({ status: "SUBMITTED", item_count: itemCount }), items: [], attachment_file_ids: [] } };
      }
      if (c.url === "/work-plans/daily/p1/approve") {
        return apiError(422, "PLAN_EMPTY", "Jadwal belum berisi pekerjaan; tambahkan item sebelum diajukan.");
      }
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <DailyPlanDetailDialog plan={plan({ status: "SUBMITTED", item_count: 1 })} canPlan isLeader={false} onEdit={() => {}} onClose={() => {}} />
      </QueryClientProvider>,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Setujui jadwal" }));
    const confirm = await screen.findByRole("dialog", { name: "Setujui jadwal?" });
    fireEvent.click(within(confirm).getByRole("button", { name: "Setujui jadwal" }));
    expect(await screen.findByText(/Jadwal belum berisi pekerjaan/)).toBeInTheDocument();

    // Item ditambahkan: data jadwal disegarkan, galat lama tidak boleh tetap tampil.
    itemCount = 2;
    await client.invalidateQueries({ queryKey: ["daily-plans"] });
    await waitFor(() => expect(screen.queryByText(/Jadwal belum berisi pekerjaan/)).toBeNull());
    expect(calls.some((c) => c.url === "/work-plans/daily/p1" && c.method === "get")).toBe(true);
  });
});

describe("hapus item jadwal", () => {
  it("Hapus pada baris item meminta konfirmasi sebelum menghapus", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan({ status: "DRAFT", item_count: 1 }), items: [item], attachment_file_ids: [] } };
      if (c.url === "/work-plans/items/i1" && c.method === "delete") return { data: {} };
    });
    renderDialog({ plan: plan({ item_count: 1 }) });
    const daftar = await screen.findByLabelText("Daftar pekerjaan");
    fireEvent.click(await within(daftar).findByRole("button", { name: "Hapus" }));
    expect(calls.some((c) => c.method === "delete")).toBe(false);
    const confirm = await screen.findByRole("dialog", { name: "Hapus pekerjaan?" });
    expect(calls.some((c) => c.method === "delete")).toBe(false);
    fireEvent.click(within(confirm).getByRole("button", { name: "Hapus" }));
    await waitFor(() => expect(calls.some((c) => c.method === "delete" && c.url === "/work-plans/items/i1")).toBe(true));
  });
});

describe("salin jadwal ke hari lain", () => {
  it("tanggal ketikan dd/mm/yyyy diterima dan menyalin ke semua hari sampai tanggal itu", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan({ status: "APPROVED", item_count: 1 }), items: [item], attachment_file_ids: [] } };
      if (c.url === "/work-plans/daily/p1/copy") return { data: [] };
    });
    renderDialog({ plan: plan({ status: "APPROVED", item_count: 1 }) });
    fireEvent.click(await screen.findByRole("button", { name: "Salin ke hari lain" }));
    const input = screen.getByLabelText("Salin setiap hari sampai tanggal");
    fireEvent.change(input, { target: { value: "01/11/2026" } });
    fireEvent.click(screen.getByRole("button", { name: "Salin" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/work-plans/daily/p1/copy")).toBe(true));
    const body = calls.find((c) => c.url === "/work-plans/daily/p1/copy")?.data as { work_dates: string[] };
    expect(body.work_dates[0]).toBe(new Date(new Date(`${todayIso}T00:00:00Z`).getTime() + 86400000).toISOString().slice(0, 10));
    expect(body.work_dates[body.work_dates.length - 1]).toBe("2026-11-01");
  });

  it("tanggal yang tidak valid ditolak dengan pesan Indonesia, bukan pesan peramban", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan({ status: "APPROVED", item_count: 1 }), items: [item], attachment_file_ids: [] } };
    });
    renderDialog({ plan: plan({ status: "APPROVED", item_count: 1 }) });
    fireEvent.click(await screen.findByRole("button", { name: "Salin ke hari lain" }));
    fireEvent.change(screen.getByLabelText("Salin setiap hari sampai tanggal"), { target: { value: "31/02/2026" } });
    fireEvent.click(screen.getByRole("button", { name: "Salin" }));
    expect(await screen.findByText(/Tanggal tidak valid/)).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/work-plans/daily/p1/copy")).toBe(false);
  });
});

describe("item jadwal: lintang dan bujur", () => {
  it("lintang di luar -90..90 ditolak sebelum dikirim", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan({ item_count: 0 }), items: [], attachment_file_ids: [] } };
      if (c.url === "/work-plans/form-options") return { data: { divisions: [], teams: [], orders: [] } };
      if (c.url === "/work-types") return { data: [] };
      if (c.url === "/work-plans/daily/p1/prerequisite-options") return { data: [] };
    });
    renderDialog({ plan: plan({ item_count: 0 }) });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah pekerjaan" }));
    fireEvent.change(screen.getByLabelText("Judul titik"), { target: { value: "Titik uji" } });
    fireEvent.change(screen.getByLabelText("Latitude titik (opsional)"), { target: { value: "95" } });
    fireEvent.change(screen.getByLabelText("Longitude titik (opsional)"), { target: { value: "106" } });
    fireEvent.click(screen.getByRole("button", { name: "Simpan pekerjaan" }));
    expect(await screen.findByText(/Lintang tidak valid\. Harus antara -90 dan 90/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post" && c.url.endsWith("/items"))).toBe(false);
  });
});
