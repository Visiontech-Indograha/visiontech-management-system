import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextAreaField, TextField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { ListBlock, ListPair } from "@/components/molecules/ListBlock";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { TextBlock } from "@/components/molecules/TextBlock";
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
} from "@/services/dailyPlanService";
import { DailyItemsPanel } from "./DailyItemsPanel";

const ACTION_LABEL: Record<DailyAction, string> = { submit: "Ajukan", approve: "Setujui", start: "Mulai", complete: "Selesai" };

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

  return (
    <VmsDialog open title={`${p.team_name} · ${formatDate(p.work_date)}`} onClose={onClose}>
      <div className="space-y-4 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={p.status} />
          <TextBlock as="span" className="text-mist">{p.division_name}</TextBlock>
        </div>
        {p.rejection_reason && p.status === "DRAFT" && (
          <TextBlock className="rounded-control bg-warning-bg px-3 py-2 text-warning">Dikembalikan PM: {p.rejection_reason}</TextBlock>
        )}
        <ListBlock as="dl" className="space-y-1">
          <ListPair>Lokasi: {p.site_name} ({Number(p.site_lat).toFixed(5)}, {Number(p.site_lng).toFixed(5)})</ListPair>
          <ListPair>Jam kerja: {p.clock_in_time.slice(0, 5)}–{p.clock_out_time.slice(0, 5)} · radius absen {p.attendance_radius_m} m</ListPair>
          <ListPair>Ketua: {p.leader_name}</ListPair>
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
            <ActionButton key={a} size="sm" disabled={transition.isPending} onClick={() => act(a)}>
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
              onClick={() => run(() => remove.mutateAsync(p.daily_plan_id), "Jadwal dihapus.", true)}
            >
              Hapus
            </ActionButton>
          )}
        </div>
      </div>
    </VmsDialog>
  );
}
