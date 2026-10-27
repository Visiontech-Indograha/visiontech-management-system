import { useState } from "react";
import { toast } from "sonner";
import { ContactLinks } from "@/components/molecules/ContactLinks";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextAreaField, TextField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { ListBlock, ListPair } from "@/components/molecules/ListBlock";
import { phaseLabel, WORK_STATE, workState } from "@/lib/workPhase";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import { formatDate } from "@/lib/format";
import {
  addDays,
  useCopyDailyPlan,
  useDailyPlan,
  useDailyTransition,
  useDeleteDailyPlan,
  useRejectDailyPlan,
  type DailyAction,
  type DailyPlan,
  wibDate,
} from "@/services/dailyPlanService";
import { DailyItemsPanel } from "./DailyItemsPanel";

const CONFIRM_MESSAGE: Record<DailyAction | "delete", string> = {
  submit: "Jadwal akan diajukan ke PM untuk disetujui.",
  approve: "Jadwal akan disetujui dan tim lapangan dapat melihat serta menjalankannya.",
  start: "Hari kerja akan dimulai. Pastikan tim sudah berada di lokasi.",
  complete: "Hari kerja akan ditutup. Pastikan laporan harian dan hasil kerja sudah lengkap.",
  delete: "Jadwal beserta pekerjaannya akan dihapus dan tidak dapat dikembalikan.",
};

const ACTION_LABEL: Record<DailyAction, string> = {
  submit: "Ajukan ke PM", approve: "Setujui jadwal", start: "Mulai hari kerja", complete: "Tutup hari kerja",
};

/** Detail jadwal harian + tindakan sesuai status & kedudukan (aturan akhir di API). */
export function DailyPlanDetailDialog({ plan, canPlan, isLeader, onEdit, onClose }: {
  plan: DailyPlan;
  canPlan: boolean;
  isLeader: boolean;
  onEdit: () => void;
  onClose: () => void;
}) {
  const detail = useDailyPlan(plan.daily_plan_id);
  const transition = useDailyTransition();
  const reject = useRejectDailyPlan();
  const remove = useDeleteDailyPlan();
  const copy = useCopyDailyPlan();
  const [mode, setMode] = useState<"view" | "reject" | "copy">("view");
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<DailyAction | "delete" | null>(null);
  const p = detail.data ?? plan;
  const editable = canPlan && (p.status === "DRAFT" || p.status === "SUBMITTED");

  const run = async (fn: () => Promise<unknown>, done: string, close = false) => {
    setError(null);
    try {
      await fn();
      toast.success(done);
      if (close) onClose();
      else setMode("view");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };
  const act = (action: DailyAction) =>
    run(() => transition.mutateAsync({ id: p.daily_plan_id, action }), `Jadwal: ${ACTION_LABEL[action].toLowerCase()}.`);

  const actions: DailyAction[] = [
    ...(canPlan && p.status === "DRAFT" ? (["submit"] as const) : []),
    ...(editable ? (["approve"] as const) : []),
    ...(isLeader && p.status === "APPROVED" ? (["start"] as const) : []),
    ...((isLeader || canPlan) && p.status === "ONGOING" ? (["complete"] as const) : []),
  ];

  const pct = p.progress_pct ?? 0;
  const state = WORK_STATE[workState(p, wibDate())];

  return (
    <VmsDialog open title={`${p.team_name} · ${formatDate(p.work_date)}`} onClose={onClose}>
      <div className="space-y-4 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={p.status} />
          <TextBlock as="span" className="text-mist">{p.division_name}</TextBlock>
        </div>
        {/* Progres penyelesaian */}
        <div className="rounded-control border border-line p-3">
          <div className="mb-1 flex items-baseline justify-between">
            <TextBlock as="span" className={`flex items-center gap-2 font-semibold ${state.text}`}>
              <TextBlock as="span" className={`h-2.5 w-2.5 rounded-full ${state.dot}`} />
              {state.label}
            </TextBlock>
            <TextBlock as="span" className={`text-lg font-semibold ${state.text}`}>{pct}%</TextBlock>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-line" aria-hidden="true">
            <div className={`h-full rounded-full ${state.bar} transition-all duration-700`} style={{ width: `${pct}%` }} />
          </div>
          <TextBlock as="span" className="mt-1 block text-xs text-mist">
            {`${p.done_count} dari ${p.item_count} pekerjaan selesai${(p.phases ?? []).length ? ` · ${(p.phases ?? []).map(phaseLabel).join(", ")}` : ""}`}
          </TextBlock>
        </div>
        {p.rejection_reason && p.status === "DRAFT" && (
          <TextBlock className="rounded-control bg-warning-bg px-3 py-2 text-warning">Dikembalikan PM: {p.rejection_reason}</TextBlock>
        )}
        <ListBlock as="dl" className="space-y-1">
          <ListPair>
            Lokasi: {p.site_name ?? "Belum ditentukan"}
            {p.site_lat != null && p.site_lng != null && ` (${Number(p.site_lat).toFixed(5)}, ${Number(p.site_lng).toFixed(5)})`}
          </ListPair>
          <ListPair>
            Jam kerja: {p.clock_in_time.slice(0, 5)}–{p.clock_out_time.slice(0, 5)}
            {p.attendance_radius_m != null && ` · radius absen ${p.attendance_radius_m} m`}
          </ListPair>
          <ListPair>
            Ketua: {p.leader_name} <ContactLinks phone={p.leader_phone} name={p.leader_name} />
          </ListPair>
        </ListBlock>

        <DailyItemsPanel detail={detail.data} loading={detail.isPending} canPlan={canPlan} />

        {error && <TextBlock role="alert" className="text-danger">{error}</TextBlock>}

        {mode === "reject" && (
          <FormBlock
            className="space-y-2"
            onSubmit={(e) => {
              e.preventDefault();
              const reason = String(new FormData(e.currentTarget).get("reason") ?? "").trim();
              if (reason.length < 3) return setError("Alasan minimal 3 huruf.");
              void run(() => reject.mutateAsync({ id: p.daily_plan_id, reason }), "Jadwal dikembalikan ke draf.");
            }}
          >
            <TextAreaField name="reason" label="Alasan dikembalikan" />
            <ActionButton type="submit" size="sm" disabled={reject.isPending}>Kembalikan ke draf</ActionButton>
          </FormBlock>
        )}
        {mode === "copy" && (
          <FormBlock
            className="space-y-2"
            onSubmit={(e) => {
              e.preventDefault();
              const from = String(new FormData(e.currentTarget).get("until") ?? "");
              const dates: string[] = [];
              for (let d = addDays(p.work_date, 1); from && d <= from; d = addDays(d, 1)) dates.push(d);
              if (!dates.length) return setError("Pilih tanggal akhir setelah tanggal jadwal ini.");
              void run(() => copy.mutateAsync({ id: p.daily_plan_id, work_dates: dates }), `${dates.length} jadwal draf dibuat.`, true);
            }}
          >
            <TextField name="until" label="Salin setiap hari sampai tanggal" type="date" />
            <ActionButton type="submit" size="sm" disabled={copy.isPending}>Salin</ActionButton>
          </FormBlock>
        )}

        <div className="flex flex-wrap gap-2 border-t border-line pt-3">
          {actions.map((a) => (
            <ActionButton key={a} size="sm" disabled={transition.isPending} onClick={() => setConfirm(a)}>
              {ACTION_LABEL[a]}
            </ActionButton>
          ))}
          {canPlan && (p.status === "SUBMITTED" || p.status === "APPROVED") && (
            <ActionButton size="sm" variant="outline" onClick={() => setMode("reject")}>Kembalikan</ActionButton>
          )}
          {editable && <ActionButton size="sm" variant="outline" onClick={onEdit}>Ubah</ActionButton>}
          {canPlan && <ActionButton size="sm" variant="outline" onClick={() => setMode("copy")}>Salin ke hari lain</ActionButton>}
          {editable && (
            <ActionButton
              size="sm"
              variant="ghost"
              disabled={remove.isPending}
              onClick={() => setConfirm("delete")}
            >
              Hapus
            </ActionButton>
          )}
        </div>
      </div>
      <ConfirmDialog
        open={confirm !== null}
        title={confirm === "delete" ? "Hapus jadwal?" : confirm ? `${ACTION_LABEL[confirm]}?` : ""}
        message={confirm ? CONFIRM_MESSAGE[confirm] : ""}
        confirmLabel={confirm === "delete" ? "Hapus" : confirm ? ACTION_LABEL[confirm] : ""}
        danger={confirm === "delete"}
        busy={transition.isPending || remove.isPending}
        onConfirm={async () => {
          const chosen = confirm;
          if (!chosen) return;
          if (chosen === "delete") await run(() => remove.mutateAsync(p.daily_plan_id), "Jadwal dihapus.", true);
          else await act(chosen);
          setConfirm(null);
        }}
        onClose={() => setConfirm(null)}
      />
    </VmsDialog>
  );
}
