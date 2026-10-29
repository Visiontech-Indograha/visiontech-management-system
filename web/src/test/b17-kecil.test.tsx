import userEvent from "@testing-library/user-event";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { DailyPlanDetailDialog } from "@/components/organisms/work-plans/DailyPlanDetailDialog";
import type { DailyPlan } from "@/services/dailyPlanService";
import { mockMe } from "@/app/mockSession";
import { WorkCompletionDetailModal } from "@/components/organisms/work-completions/WorkCompletionDetailModal";
import { useSession } from "@/stores/sessionStore";
import { mockApi, renderRoute } from "./utils";

/** Temuan kecil siklus 2 (B17): T-5 judul tanpa "null", T-6 hapus draf lampau, tombol persetujuan per peran. */

const todayIso = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
const pastIso = (days: number) => {
  const [y, m, d] = todayIso.split("-").map(Number);
  return new Date(Date.UTC(y!, m! - 1, d! + days)).toISOString().slice(0, 10);
};
const dayLabel = (iso: string) =>
  new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" })
    .format(new Date(`${iso}T00:00:00Z`));

const plan = (over: Partial<DailyPlan> = {}): DailyPlan => ({
  daily_plan_id: "p1", division_id: "d1", division_name: "Sipil", team_id: "t1", team_name: "Tim Alpha",
  leader_employee_id: "e-lead", leader_name: "Agus", work_date: todayIso, site_name: "Gardu Induk Minas",
  site_lat: "1.4700000", site_lng: "101.4500000", attendance_radius_m: 150, clock_in_time: "07:00:00",
  clock_out_time: "16:00:00", status: "DRAFT", created_by_id: "e-pm", item_count: 1, done_count: 0, progress_pct: 0,
  phases: [], can_manage: true, ...over,
} as DailyPlan);

const item = {
  item_id: "i1", task_phase: "INSTALLATION", title: "Titik CCTV 01", status: "TODO", completed_qty: "0",
  target_qty: "1", completion_id: null, depends_on_item_id: null, rollover_approval_status: null,
  location_name: null, site_lat: null, site_lng: null,
};

function renderDialog(p: DailyPlan, role: { canPlan: boolean; isLeader: boolean }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <DailyPlanDetailDialog plan={p} canPlan={role.canPlan} isLeader={role.isLeader} onEdit={() => {}} onClose={() => {}} />
    </QueryClientProvider>,
  );
}

// Peran web: PM/OM memegang create:plan & can_manage (divisi mereka); ketua/HR/anggota tidak.
const ROLES = {
  pm: { canPlan: true, isLeader: false, can_manage: true },
  om: { canPlan: true, isLeader: false, can_manage: true },
  ketua: { canPlan: false, isLeader: true, can_manage: false },
  hr: { canPlan: false, isLeader: false, can_manage: false },
  anggota: { canPlan: false, isLeader: false, can_manage: false },
} as const;

describe("T-5 judul jadwal tanpa lokasi", () => {
  it("dialog hari menampilkan fallback lokasi, bukan 'null'", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [plan({ site_name: null })] };
      if (c.url === "/work-plans/form-options") {
        return { data: { divisions: [{ division_id: "d1", name: "Sipil" }], teams: [], orders: [] } };
      }
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel(todayIso)}: 1 jadwal` }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Tim Alpha · Lokasi belum ditentukan")).toBeInTheDocument();
    expect(within(dialog).queryByText(/null/)).not.toBeInTheDocument();
  });
});

describe("persetujuan jadwal per peran & status", () => {
  for (const [role, r] of Object.entries(ROLES)) {
    for (const status of ["DRAFT", "SUBMITTED", "APPROVED"] as const) {
      it(`${role} · ${status}: ${r.can_manage ? "melihat" : "tidak melihat"} Setujui, tidak pernah Ajukan`, async () => {
        mockApi((c) => {
          if (c.url === "/work-plans/daily/p1") {
            return { data: { ...plan({ status, can_manage: r.can_manage }), items: [item], attachment_file_ids: [] } };
          }
        });
        renderDialog(plan({ status, can_manage: r.can_manage }), r);
        await screen.findByText("Gardu Induk Minas", { exact: false });
        const approveShown = r.can_manage && (status === "DRAFT" || status === "SUBMITTED");
        if (approveShown) expect(screen.getByRole("button", { name: "Setujui jadwal" })).toBeEnabled();
        else expect(screen.queryByRole("button", { name: "Setujui jadwal" })).not.toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Ajukan ke PM" })).not.toBeInTheDocument();
      });
    }
  }
});

describe("T-6 hapus draf bertanggal lampau", () => {
  it("PM/OM melihat tombol Hapus pada draf tanggal lampau", async () => {
    const past = pastIso(-2);
    mockApi((c) => {
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan({ work_date: past }), items: [item], attachment_file_ids: [] } };
    });
    renderDialog(plan({ work_date: past }), ROLES.pm);
    expect(await screen.findByRole("button", { name: "Hapus" })).toBeEnabled();
  });

  it("ketua tidak melihat tombol Hapus", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/daily/p1") return { data: { ...plan({ can_manage: false }), items: [item], attachment_file_ids: [] } };
    });
    renderDialog(plan({ can_manage: false }), ROLES.ketua);
    await screen.findByText("Gardu Induk Minas", { exact: false });
    expect(screen.queryByRole("button", { name: "Hapus" })).not.toBeInTheDocument();
  });
});

describe("T-6 alur penuh dari matriks minggu", () => {
  it("PM membuka draf lampau dari kalender lalu melihat tombol Hapus", async () => {
    const past = pastIso(-2);
    const pastPlan = plan({ work_date: past, status: "DRAFT", can_manage: true });
    mockApi((c) => {
      if (c.url === "/work-plans/daily" && c.method === "get") return { data: [pastPlan] };
      if (c.url === "/work-plans/form-options") {
        return { data: { divisions: [{ division_id: "d1", name: "Sipil" }], teams: [{ team_id: "t1", name: "Tim Alpha", division_id: "d1", leader_employee_id: "e-lead", leader_name: "Agus" }], orders: [] } };
      }
      if (c.url === "/work-plans/daily/p1") return { data: { ...pastPlan, items: [item], attachment_file_ids: [] } };
    });
    renderRoute("/work-plans", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: `${dayLabel(past)}: 1 jadwal` }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Tim Alpha/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("button", { name: "Hapus" })).toBeEnabled();
  });
});

// Matriks persetujuan cuti per peran V2 (ALLOWED_REVIEW_ROLES di API) × status.
const leaveFor = (status: string) => ({
  leave_id: "l1", employee_id: "e1", employee_name: "Uji Ketua", employee_no: "N1", division_name: "Sipil",
  leave_type: "ANNUAL", start_date: "2026-10-29", end_date: "2026-10-30", total_days: 2, reason: "Keperluan keluarga",
  status, attachment_path: null, reviewed_by_name: null, review_note: null, rejection_note: null, cancel_note: null,
  conflicts: [], create_at: "2026-10-27T10:00:00Z",
});
const asRole = (role: string) => ({ ...mockMe("PM")!, role });
const LEAVE_CASES: Array<[string, string, boolean]> = [
  ["PROJECT_MANAGER", "PENDING", true],
  ["PROJECT_MANAGER", "APPROVED_BY_PM", false],
  ["OPERATIONAL_MANAGER", "PENDING", true],
  ["OPERATIONAL_MANAGER", "APPROVED_BY_PM", true],
  ["ADMIN_HR_GA", "PENDING", true],
  ["ADMIN_HR_GA", "APPROVED_BY_PM", true],
  ["SUPER_ADMIN", "APPROVED_BY_PM", true],
  ["TEAM_LEADER", "PENDING", false],
  ["EMPLOYEE", "PENDING", false],
  ["FINANCE", "PENDING", false],
  ["OPS", "PENDING", false],
];
describe("persetujuan cuti per peran x status", () => {
  for (const [role, status, shown] of LEAVE_CASES) {
    it(`${role} · ${status}: tombol tinjau ${shown ? "tampil" : "tidak tampil"}`, async () => {
      mockApi((c) => {
        if (c.url === "/leaves" && c.method === "get") return { data: [leaveFor(status)] };
        if (c.url?.startsWith("/leaves/balance")) return { data: { total_quota: 12, used_quota: 0, remaining_quota: 12, period_year: 2026 } };
      });
      renderRoute("/leaves", { me: asRole(role) });
      await screen.findByText("Uji Ketua");
      const btn = screen.queryByRole("button", { name: "Tinjau cuti Uji Ketua" });
      if (shown) expect(btn).toBeInTheDocument();
      else expect(btn).not.toBeInTheDocument();
    });
  }
});

// BAST: tombol Tandatangani (PM) hanya untuk PM/OM/admin setelah ketua menandatangani (API sign_order).
const bastOrder = {
  completion_id: "wc1", order_number: "PHR-01", project_title: "CCTV", division_name: "Sipil", pm_name: "Dian",
  site_address: "Jl. Uji 1", site_lat: "1.4", site_lng: "101.4", start_work_date: todayIso, end_work_date: todayIso,
  unit_measure: "Titik", summary_notes: "Selesai", realization_photos_json: [], signature_hash: null,
  leader_signed_at: "2026-10-20T02:00:00Z", leader_signer_name: "Agus", pm_signed_at: null, pm_signer_name: null,
  status: "ONGOING", items: [], materials: [],
};
const BAST_CASES: Array<[string, boolean]> = [
  ["PROJECT_MANAGER", true], ["OPERATIONAL_MANAGER", true], ["SUPER_ADMIN", true],
  ["OPS", false], ["ADMIN", false], ["ADMIN_HR_GA", false], ["TEAM_LEADER", false], ["EMPLOYEE", false],
];
describe("BAST tombol tanda tangan PM per peran", () => {
  for (const [role, shown] of BAST_CASES) {
    it(`${role}: Tandatangani BAST ${shown ? "tampil" : "tidak tampil"}`, async () => {
      mockApi((c) => {
        if (c.url === "/work-completions/wc1") return { data: bastOrder };
      });
      useSession.setState({ me: { ...mockMe("PM")!, role }, ready: true });
      render(
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <WorkCompletionDetailModal completionId="wc1" onClose={() => {}} canManage />
        </QueryClientProvider>,
      );
      const tabs = await screen.findAllByRole("tab");
      await userEvent.click(tabs[tabs.length - 1]!);
      const btn = await screen.findByRole("button", { name: /Tandatangani BAST/ }, { timeout: 5000 }).catch(() => null);
      if (shown) expect(btn).not.toBeNull();
      else expect(btn).toBeNull();
    });
  }
});
