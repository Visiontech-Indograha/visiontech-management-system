import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { displayPct, workState } from "@/lib/workPhase";
import { parseTargetQty } from "@/lib/quantity";
import { mockApi, renderRoute } from "./utils";

const todayIso = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
const dayLabel = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" })
  .format(new Date(`${todayIso}T00:00:00Z`));
const options = {
  divisions: [{ division_id: "d1", name: "Sipil" }],
  teams: [{ team_id: "t1", name: "Tim Alpha", division_id: "d1", leader_employee_id: "e-lead", leader_name: "Agus" }],
  orders: [],
};
const plan = (over: Record<string, unknown> = {}) => ({
  daily_plan_id: "p1", division_id: "d1", division_name: "Sipil", team_id: "t1", team_name: "Tim Alpha",
  leader_employee_id: "e-lead", leader_name: "Agus", work_date: todayIso, site_name: "Gardu Induk Minas",
  site_lat: "1.4700000", site_lng: "101.4500000", attendance_radius_m: 150, clock_in_time: "07:00:00",
  clock_out_time: "16:00:00", status: "ONGOING", created_by_id: "e-pm", item_count: 2, done_count: 1,
  progress_pct: 100, ...over,
});

describe("persen jadwal (W6)", () => {
  it("item yang dipindah hari tidak membuat jadwal 'Selesai 100%'", () => {
    const p = { status: "ONGOING", work_date: todayIso, item_count: 2, done_count: 1, progress_pct: 100 };
    expect(displayPct(p)).toBe(99);
    expect(workState(p, todayIso)).toBe("ONGOING");
  });

  it("100% dan Selesai hanya bila semua item (termasuk yang dipindah) sudah DONE", () => {
    const p = { status: "COMPLETED", work_date: todayIso, item_count: 2, done_count: 2, progress_pct: 100 };
    expect(displayPct(p)).toBe(100);
    expect(workState(p, todayIso)).toBe("DONE");
  });

  it("jadwal selesai sebagian tetap berlabel Selesai sebagian", () => {
    const p = { status: "COMPLETED", work_date: todayIso, item_count: 2, done_count: 1, progress_pct: 100 };
    expect(workState(p, todayIso)).toBe("PARTIAL");
  });

  it("detail jadwal menampilkan keadaan 'Berjalan' dan 99%, bukan Selesai 100%", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan()] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan(), items: [], attachment_file_ids: [] } };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: 1 jadwal` }));
fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Tim Alpha/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getAllByText("Berjalan").length).toBeGreaterThan(0);
    expect(within(dialog).getByText("99%")).toBeInTheDocument();
    expect(within(dialog).queryByText("Selesai")).toBeNull();
  });
});

describe("volume target (W2)", () => {
  it("koma diterima sebagai desimal dan dinormalisasi ke titik", () => {
    expect(parseTargetQty("1,5")).toEqual({ ok: true, value: "1.5" });
    expect(parseTargetQty(" 12 ")).toEqual({ ok: true, value: "12" });
  });

  it("menolak nol, lebih dari batas, dan desimal lebih dari 2 angka, dengan pesan jelas", () => {
    expect(parseTargetQty("")).toMatchObject({ ok: false });
    expect(parseTargetQty("0")).toEqual({ ok: false, message: "Target volume harus lebih dari 0." });
    expect(parseTargetQty("99999999999")).toEqual({ ok: false, message: "Target volume maksimal 99.999.999." });
    expect(parseTargetQty("1.234")).toEqual({ ok: false, message: "Target volume maksimal 2 angka di belakang koma." });
    expect(parseTargetQty("abc")).toMatchObject({ ok: false });
  });

  it("form item menampilkan galat di kolom target dan tidak mengirim permintaan", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan({ status: "DRAFT", done_count: 0, progress_pct: 0, item_count: 0 })] };
      if (c.url === "/work-plans/form-options") return { data: options };
      if (c.url === "/work-types") return { data: [] };
      if (c.url === "/work-plans/daily/p1/prerequisite-options") return { data: [] };
      if (c.url === "/work-plans/daily/p1") {
        return { data: { ...plan({ status: "DRAFT", done_count: 0, progress_pct: 0, item_count: 0 }), items: [], attachment_file_ids: [] } };
      }
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel}: 1 jadwal` }));
fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Tim Alpha/ }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(await within(dialog).findByRole("button", { name: "Tambah pekerjaan" }));
    fireEvent.change(within(dialog).getByLabelText("Judul titik"), { target: { value: "Titik uji" } });
    fireEvent.change(within(dialog).getByLabelText("Target volume"), { target: { value: "1.234" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan pekerjaan" }));
    expect(await within(dialog).findByText("Target volume maksimal 2 angka di belakang koma.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post" && c.url.endsWith("/items"))).toBe(false);
  });
});
