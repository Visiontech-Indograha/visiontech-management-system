import { useState, type ReactNode } from "react";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { useTransition, type Transition, type WorkPlan } from "@/services/workPlanService";
import { IncidentDialog, IncidentPanel } from "./IncidentPanel";
import { OvertimeDialog, OvertimePanel } from "./OvertimePanel";
import { ReasonDialog } from "./PlanFormDialogs";
import { PlanPreviewDialog } from "./PlanPreviewDialog";
import { PlanRevisionHistory } from "./PlanRevisionHistory";
import { PlanRevisionPanel } from "./PlanRevisionPanel";
import { ActionButton } from "@/components/molecules/ActionButton";
import { InlineLink } from "@/components/molecules/Links";
import { TextBlock } from "@/components/molecules/TextBlock";

const CANCELLABLE = ["PUBLISHED", "APPEALED", "ACCEPTED", "IN_PROGRESS", "COMPLETION_REVIEW"];

type Dialogs =
  | {
      kind: "preview" | "incident" | "overtime" | "publish" | "approve";
    }
  | { kind: "reason"; action: Transition; title: string; label: string }
  | null;

/**
 * Tindakan sesuai prototype/js/workplans.js `controls`. Tindakan pengelola memakai izin create:plan;
 * tindakan ketua hanya untuk karyawan yang menjadi ketua pada SK ini (`leader_employee_id`) —
 * kewenangan mengikuti SK, bukan jabatan. API tetap menjadi penjaga terakhir.
 */
export function PlanActionsPanel({ plan }: { plan: WorkPlan }) {
  const { me } = useSession();
  const canManage = !!me?.permissions.includes("create:plan");
  const isLeader = !!me?.employee_id && me.employee_id === plan.leader_employee_id;
  // Insiden & lembur boleh diajukan anggota tim; PM/pengelola tidak melihatnya kecuali ia ketua SK ini.
  const isCrew = isLeader || !canManage;
  const transition = useTransition(plan.id);
  const [dialog, setDialog] = useState<Dialogs>(null);
  const s = plan.status;

  const run = async (action: Transition, done: string): Promise<boolean> => {
    try {
      await transition.mutateAsync({ action, row_version: plan.row_version });
      toast.success(done);
      return true;
    } catch (err) {
      toast.error(errorMessage(err));
      return false;
    }
  };
  const reason = (action: Transition, title: string, label: string) => () => setDialog({ kind: "reason", action, title, label });
  const busy = transition.isPending;

  const manager: ReactNode[] = [];
  const leader: ReactNode[] = [];
  if (canManage) {
    if (s === "DRAFT") {
      manager.push(
        <ActionButton key="preview" variant="outline" onClick={() => setDialog({ kind: "preview" })}>
          Sunting rencana kerja
        </ActionButton>,
        <ActionButton key="publish" onClick={() => setDialog({ kind: "publish" })} disabled={busy}>
          Terbitkan rencana kerja
        </ActionButton>,
      );
      // Draf revisi (pernah terbit) tidak bisa diarsip; pembatalannya lewat "Batalkan pekerjaan".
      if (plan.revision === 1)
        manager.push(
          <ActionButton key="archive" variant="outline" onClick={reason("archive", "Arsipkan draf", "Alasan pengarsipan")}>
            Arsipkan draf
          </ActionButton>,
        );
    }
    if (s === "APPEALED")
      manager.push(
        <ActionButton key="revise" onClick={() => run("revise", "Revisi dibuka. Ubah isi rencana kerja lalu terbitkan lagi.")} disabled={busy}>
          Buka revisi
        </ActionButton>,
      );
    if (s === "COMPLETION_REVIEW")
      manager.push(
        <ActionButton key="approve-completion" onClick={() => setDialog({ kind: "approve" })} disabled={busy}>
          Setujui penutupan
        </ActionButton>,
        <ActionButton
          key="return-completion"
          variant="outline"
          onClick={reason("return-completion", "Kembalikan (perlu perbaikan)", "Catatan untuk ketua tim")}
        >
          Kembalikan (perlu perbaikan)
        </ActionButton>,
      );
    if (["PUBLISHED", "APPEALED", "ACCEPTED", "IN_PROGRESS"].includes(s))
      manager.push(
        <ActionButton key="revise-plan" asChild>
          <InlineLink to={`/work-plans/${plan.id}/revise`}>Revisi rencana kerja</InlineLink>
        </ActionButton>,
      );
    if (CANCELLABLE.includes(s) || (s === "DRAFT" && plan.revision > 1))
      manager.push(
        <ActionButton key="cancel" variant="destructive" onClick={reason("cancel", "Batalkan pekerjaan", "Alasan pembatalan")}>
          Batalkan pekerjaan
        </ActionButton>,
      );
  }
  // Alur SK v2: Terima SK / Ajukan adendum dilakukan ketua di aplikasi HP; status Berjalan otomatis.
  if (isCrew && s === "IN_PROGRESS")
    leader.push(
      <ActionButton key="incident" variant="destructive" onClick={() => setDialog({ kind: "incident" })}>
        Lapor Insiden/HSE
      </ActionButton>,
    );
  if (isCrew && s === "IN_PROGRESS")
    leader.push(
      <ActionButton key="overtime" variant="outline" onClick={() => setDialog({ kind: "overtime" })}>
        Ajukan Lembur
      </ActionButton>,
    );

  return (
    <aside className="space-y-4">
      {/* Mode presentasi laporan (M5) — prototipe: semua peran kecuali petugas aset. */}
      {s === "COMPLETED" && me?.role !== "ASSET" && (
        <ActionButton asChild className="w-full">
          <InlineLink to={`/work-plans/${plan.id}/presentation`}>Mode presentasi laporan</InlineLink>
        </ActionButton>
      )}
      <PlanRevisionPanel plan={plan} />
      <PlanRevisionHistory planId={plan.id} />
      <IncidentPanel plan={plan} />
      <OvertimePanel plan={plan} />
      {manager.length > 0 && (
        <section aria-label="Tindakan PM" className="rounded-panel border border-line bg-surface shadow-card p-4">
          <TextBlock as="h2" className="mb-3 text-base font-semibold">Tindakan PM</TextBlock>
          {s === "PUBLISHED" && (
            <TextBlock className="mb-3 rounded-control bg-warning-bg px-3 py-2 text-sm text-warning">
              Notifikasi sudah dikirim ke ketua tim dan anggota. Menunggu ketua meninjau rencana kerja di aplikasi HP lalu menekan{" "}
              <TextBlock as="strong">Terima rencana kerja</TextBlock> atau <TextBlock as="strong">Ajukan revisi</TextBlock>.
            </TextBlock>
          )}
          {s === "APPEALED" && (
            <TextBlock className="mb-3 rounded-control bg-warning-bg px-3 py-2 text-sm text-warning">
              Ketua tim meminta revisi{plan.appeal_reason ? `: "${plan.appeal_reason}"` : ""}. Buka revisi, ubah isi rencana kerja, lalu terbitkan lagi.
            </TextBlock>
          )}
          {s === "ACCEPTED" && (
            <TextBlock className="mb-3 rounded-control bg-canvas px-3 py-2 text-sm text-mist">
              Rencana Kerja diterima ketua tim. Status otomatis menjadi Berjalan pada {formatDate(plan.period_start)}.
            </TextBlock>
          )}
          <div className="flex flex-col gap-2 [&>button]:w-full">{manager}</div>
        </section>
      )}
      {leader.length > 0 && (
        <section aria-label="Tindakan ketua tim" className="rounded-panel border border-line bg-surface shadow-card p-4">
          <TextBlock as="h2" className="mb-3 text-base font-semibold">Tindakan ketua tim</TextBlock>
          <div className="flex flex-col gap-2 [&>button]:w-full">{leader}</div>
        </section>
      )}
      {dialog?.kind === "publish" && (
        <VmsDialog
          open
          title="Terbitkan rencana kerja?"
          onClose={() => setDialog(null)}
          footer={
            <>
              <ActionButton variant="outline" onClick={() => setDialog(null)} disabled={busy}>
                Batal
              </ActionButton>
              <ActionButton
                onClick={async () => {
                  // Tetap terbuka bila gagal agar pesan & tombol ulang terlihat (CELAH 6, docs/28).
                  if (await run("publish", "Rencana Kerja diterbitkan dan ditandatangani. Notifikasi dikirim ke ketua tim dan anggota.")) setDialog(null);
                }}
                disabled={busy}
              >
                {busy ? "Menerbitkan..." : "Ya, terbitkan"}
              </ActionButton>
            </>
          }
        >
          <TextBlock className="text-sm text-mist">
            Rencana Kerja <TextBlock as="strong" className="text-ink">{plan.title}</TextBlock> akan diberi nomor, ditandatangani otomatis atas nama Anda, dan
            notifikasinya dikirim ke ketua tim serta semua anggota. Setelah terbit, isi rencana kerja tidak dapat diubah — perubahan hanya lewat
            revisi.
          </TextBlock>
        </VmsDialog>
      )}
      {dialog?.kind === "preview" && (
        <PlanPreviewDialog
          title={`Sunting rencana kerja — ${plan.title}`}
          path={`/work-plans/${plan.id}/preview`}
          editTo={`/work-plans/${plan.id}/edit`}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.kind === "approve" && (
        <VmsDialog
          open
          title="Setujui penutupan?"
          onClose={() => setDialog(null)}
          footer={
            <>
              <ActionButton variant="outline" onClick={() => setDialog(null)} disabled={busy}>
                Batal
              </ActionButton>
              <ActionButton
                disabled={busy}
                onClick={async () => {
                  if (await run("approve-completion", "Pekerjaan selesai. Laporan akhir ditandatangani; tim dan aset dilepas."))
                    setDialog(null);
                }}
              >
                {busy ? "Menyimpan..." : "Ya, setujui"}
              </ActionButton>
            </>
          }
        >
          <TextBlock className="text-sm text-mist">
            Laporan akhir <TextBlock as="strong" className="text-ink">{plan.title}</TextBlock> akan dikunci dan ditandatangani ketua tim serta Anda. Rencana Kerja
            yang berlaku menjadi tidak berlaku, ketua & anggota bebas dipilih untuk rencana kerja baru, dan status menjadi Selesai.
          </TextBlock>
        </VmsDialog>
      )}
      {dialog?.kind === "incident" && <IncidentDialog plan={plan} onClose={() => setDialog(null)} />}
      {dialog?.kind === "overtime" && <OvertimeDialog plan={plan} onClose={() => setDialog(null)} />}
      {dialog?.kind === "reason" && (
        <ReasonDialog plan={plan} action={dialog.action} title={dialog.title} label={dialog.label} onClose={() => setDialog(null)} />
      )}
    </aside>
  );
}
