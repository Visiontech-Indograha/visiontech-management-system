import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/VmsDialog";
import { PageHeader } from "@/components/ui/PageHeader";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { employeeName, useActiveEmployees, useTransition, useWorkPlan, type Transition, type WorkPlan } from "./api";
import { Attachments } from "./Attachments";
import { CompletionDialog } from "./CompletionDialog";
import { FinalReportPanel, TeamCard } from "./FinalReport";
import { IncidentDialog, IncidentPanel } from "./Incidents";
import { OvertimeDialog, OvertimePanel } from "./Overtime";
import { ChangePanel, ExtensionDialog, PersonnelDialog } from "./PlanChanges";
import { AddDayDialog, EditDraftDialog, ReasonDialog, TeamDialog } from "./PlanForms";
import { DailyReports, DayPlanList } from "./DailyReports";
import { Documents } from "./Documents";
import { PlanLocationCard } from "./PlanLocation";
import { WeeklyReports } from "./WeeklyReports";

const Row = ({ label, children }: { label: string; children: ReactNode }) => (
  <div className="flex flex-col gap-0.5 border-b border-line py-2 last:border-0 md:flex-row md:justify-between md:gap-4">
    <dt className="text-mist">{label}</dt>
    <dd className="font-medium md:text-right">{children}</dd>
  </div>
);

const CANCELLABLE = ["PUBLISHED", "APPEALED", "ACCEPTED", "IN_PROGRESS", "COMPLETION_REVIEW"];

type Dialogs =
  | {
      kind: "edit" | "team" | "day" | "completion" | "extension" | "personnel" | "incident" | "overtime" | "publish";
    }
  | { kind: "reason"; action: Transition; title: string; label: string }
  | null;

export function WorkPlanDetailPage() {
  const { id = "" } = useParams();
  const plan = useWorkPlan(id);
  const employees = useActiveEmployees();
  const p = plan.data;

  return (
    <>
      <PageHeader title={p?.title ?? "Work plan"} action={p && <StatusBadge status={p.status} />} />
      <QueryState query={plan} errorText="Work plan tidak ditemukan atau Anda tidak berwenang melihatnya.">
        {p && (
          <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
            <section aria-label="Rincian SK" className="rounded-panel border border-line bg-surface shadow-card px-5 py-2">
              <dl className="text-sm">
                <Row label="Nomor SK">{p.number ?? "Belum terbit"}</Row>
                <Row label="Revisi">{p.revision}</Row>
                <Row label="Lokasi">{p.location_text}</Row>
                <Row label="Periode">
                  {formatDate(p.period_start)} – {formatDate(p.period_end)}
                </Row>
                <Row label="PM">{employeeName(employees.data, p.pm_employee_id)}</Row>
                <Row label="Ketua tim">{employeeName(employees.data, p.leader_employee_id)}</Row>
                {p.description && <Row label="Uraian">{p.description}</Row>}
                {p.appeal_reason && <Row label="Alasan banding">{p.appeal_reason}</Row>}
                {p.cancellation_reason && <Row label="Alasan pembatalan">{p.cancellation_reason}</Row>}
              </dl>
            </section>
            <PlanActions plan={p} />
          </div>
        )}
        {p && p.status !== "DRAFT" && <TeamCard plan={p} />}
        {p && ["IN_PROGRESS", "COMPLETION_REVIEW", "COMPLETED"].includes(p.status) && <FinalReportPanel plan={p} />}
        {p && <PlanLocationCard plan={p} />}
        {p && ["DRAFT", "PUBLISHED", "APPEALED", "ACCEPTED"].includes(p.status) && (
          <div className="mt-6">
            <DayPlanList plan={p} />
          </div>
        )}
        {p && <Attachments plan={p} />}
        {p && p.status !== "DRAFT" && <Documents plan={p} />}
        {p && ["IN_PROGRESS", "COMPLETION_REVIEW", "COMPLETED"].includes(p.status) && (
          <div className="mt-6 space-y-6">
            <DailyReports plan={p} />
            <WeeklyReports plan={p} />
          </div>
        )}
      </QueryState>
      <p className="mt-6">
        <Link to="/work-plans" className="font-semibold text-lens hover:underline">
          Kembali ke daftar work plan
        </Link>
      </p>
    </>
  );
}

/**
 * Tindakan sesuai prototype/js/workplans.js `controls`. Tindakan pengelola memakai izin create:plan;
 * tindakan ketua hanya untuk karyawan yang menjadi ketua pada SK ini (`leader_employee_id`) —
 * kewenangan mengikuti SK, bukan jabatan. API tetap menjadi penjaga terakhir.
 */
function PlanActions({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const canManage = !!me?.permissions.includes("create:plan");
  const isLeader = !!me?.employee_id && me.employee_id === plan.leader_employee_id;
  // Insiden & lembur boleh diajukan anggota tim; PM/pengelola tidak melihatnya kecuali ia ketua SK ini.
  const isCrew = isLeader || !canManage;
  const transition = useTransition(plan.id);
  const [dialog, setDialog] = useState<Dialogs>(null);
  const s = plan.status;

  const run = async (action: Transition, done: string) => {
    try {
      await transition.mutateAsync({ action, row_version: plan.row_version });
      toast.success(done);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  const reason = (action: Transition, title: string, label: string) => () => setDialog({ kind: "reason", action, title, label });
  const busy = transition.isPending;

  const manager: ReactNode[] = [];
  const leader: ReactNode[] = [];
  if (canManage) {
    if (s === "DRAFT") {
      manager.push(
        <Button key="publish" onClick={() => setDialog({ kind: "publish" })} disabled={busy}>
          Terbitkan SK
        </Button>,
        <Button key="edit" variant="outline" onClick={() => setDialog({ kind: "edit" })}>
          Sunting draft
        </Button>,
        <Button key="team" variant="outline" onClick={() => setDialog({ kind: "team" })}>
          Atur tim
        </Button>,
        <Button key="day" variant="outline" onClick={() => setDialog({ kind: "day" })}>
          Tambah hari
        </Button>,
        <Button key="archive" variant="outline" onClick={reason("archive", "Arsipkan draft", "Alasan pengarsipan")}>
          Arsipkan draft
        </Button>,
      );
    }
    if (s === "APPEALED")
      manager.push(
        <Button key="revise" onClick={() => run("revise", "Draft revisi dibuka.")} disabled={busy}>
          Buka draft revisi
        </Button>,
      );
    if (s === "ACCEPTED" || s === "IN_PROGRESS")
      manager.push(
        <Button key="personnel" variant="outline" onClick={() => setDialog({ kind: "personnel" })}>
          Adendum personel
        </Button>,
      );
    if (s === "COMPLETION_REVIEW")
      manager.push(
        <Button key="approve-completion" onClick={() => run("approve-completion", "Pekerjaan dinyatakan selesai.")} disabled={busy}>
          Setujui penyelesaian
        </Button>,
        <Button
          key="return-completion"
          variant="outline"
          onClick={reason("return-completion", "Kembalikan penyelesaian", "Alasan pengembalian")}
        >
          Kembalikan penyelesaian
        </Button>,
      );
    if (CANCELLABLE.includes(s))
      manager.push(
        <Button key="cancel" variant="destructive" onClick={reason("cancel", "Batalkan pekerjaan", "Alasan pembatalan")}>
          Batalkan pekerjaan
        </Button>,
      );
  }
  if (isLeader && s === "PUBLISHED")
    leader.push(
      <Button key="accept" onClick={() => run("accept", "SK diterima.")} disabled={busy}>
        Terima SK
      </Button>,
      <Button key="appeal" variant="outline" onClick={reason("appeal", "Ajukan banding", "Alasan banding")}>
        Ajukan banding
      </Button>,
    );
  if (isLeader && s === "ACCEPTED")
    leader.push(
      <Button key="start" onClick={() => run("start", "Pelaksanaan dimulai.")} disabled={busy}>
        Mulai pelaksanaan
      </Button>,
    );
  if (isLeader && (s === "ACCEPTED" || s === "IN_PROGRESS"))
    leader.push(
      <Button key="extension" variant="outline" onClick={() => setDialog({ kind: "extension" })}>
        Ajukan perpanjangan
      </Button>,
    );
  if (isCrew && s === "IN_PROGRESS")
    leader.push(
      <Button key="incident" variant="destructive" onClick={() => setDialog({ kind: "incident" })}>
        Lapor Insiden/HSE
      </Button>,
    );
  if (isCrew && s === "IN_PROGRESS")
    leader.push(
      <Button key="overtime" variant="outline" onClick={() => setDialog({ kind: "overtime" })}>
        Ajukan Lembur
      </Button>,
    );
  if (isLeader && s === "IN_PROGRESS")
    leader.push(
      <Button key="completion" onClick={() => setDialog({ kind: "completion" })}>
        Buat Laporan Akhir
      </Button>,
    );

  return (
    <aside className="space-y-4">
      {/* Mode presentasi laporan (M5) — prototipe: semua peran kecuali petugas aset. */}
      {s === "COMPLETED" && me?.role !== "ASSET" && (
        <Button asChild className="w-full">
          <Link to={`/work-plans/${plan.id}/presentation`}>Mode presentasi laporan</Link>
        </Button>
      )}
      <ChangePanel plan={plan} />
      <IncidentPanel plan={plan} />
      <OvertimePanel plan={plan} />
      {manager.length > 0 && (
        <section aria-label="Tindakan PM" className="rounded-panel border border-line bg-surface shadow-card p-4">
          <h2 className="mb-3 text-base font-semibold">Tindakan PM</h2>
          <div className="flex flex-col gap-2 [&>button]:w-full">{manager}</div>
        </section>
      )}
      {leader.length > 0 && (
        <section aria-label="Tindakan ketua tim" className="rounded-panel border border-line bg-surface shadow-card p-4">
          <h2 className="mb-3 text-base font-semibold">Tindakan ketua tim</h2>
          <div className="flex flex-col gap-2 [&>button]:w-full">{leader}</div>
        </section>
      )}
      {dialog?.kind === "publish" && (
        <Dialog
          open
          title="Terbitkan SK?"
          onClose={() => setDialog(null)}
          footer={
            <>
              <Button variant="outline" onClick={() => setDialog(null)} disabled={busy}>
                Batal
              </Button>
              <Button
                onClick={async () => {
                  await run("publish", "SK diterbitkan.");
                  setDialog(null);
                }}
                disabled={busy}
              >
                {busy ? "Menerbitkan..." : "Ya, terbitkan"}
              </Button>
            </>
          }
        >
          <p className="text-sm text-mist">
            SK <strong className="text-ink">{plan.title}</strong> akan diberi nomor dan dikirim ke ketua tim untuk diterima.
            Setelah terbit, isi SK tidak dapat diubah — perubahan hanya lewat adendum atau revisi.
          </p>
        </Dialog>
      )}
      {dialog?.kind === "edit" && <EditDraftDialog plan={plan} onClose={() => setDialog(null)} />}
      {dialog?.kind === "team" && <TeamDialog plan={plan} onClose={() => setDialog(null)} />}
      {dialog?.kind === "day" && <AddDayDialog plan={plan} onClose={() => setDialog(null)} />}
      {dialog?.kind === "completion" && <CompletionDialog plan={plan} onClose={() => setDialog(null)} />}
      {dialog?.kind === "extension" && <ExtensionDialog plan={plan} onClose={() => setDialog(null)} />}
      {dialog?.kind === "personnel" && <PersonnelDialog plan={plan} onClose={() => setDialog(null)} />}
      {dialog?.kind === "incident" && <IncidentDialog plan={plan} onClose={() => setDialog(null)} />}
      {dialog?.kind === "overtime" && <OvertimeDialog plan={plan} onClose={() => setDialog(null)} />}
      {dialog?.kind === "reason" && (
        <ReasonDialog plan={plan} action={dialog.action} title={dialog.title} label={dialog.label} onClose={() => setDialog(null)} />
      )}
    </aside>
  );
}
