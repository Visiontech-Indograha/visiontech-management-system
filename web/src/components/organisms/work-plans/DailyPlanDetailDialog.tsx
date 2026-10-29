import { useState } from "react";
import { toast } from "sonner";
import { ContactLinks } from "@/components/molecules/ContactLinks";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextAreaField, TextField } from "@/components/molecules/Field";
import { FormBlock } from "@/components/molecules/FormBlock";
import { ListBlock, ListPair } from "@/components/molecules/ListBlock";
import { displayPct, phaseLabel, WORK_STATE, workState } from "@/lib/workPhase";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { DialogCancelButton } from "@/components/molecules/DialogActions";
import { useDirtyForm } from "@/hooks/useDirtyForm";
import { parseTanggalInput } from "@/lib/inputRules";
import { ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
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
import { useExportDailyReport } from "@/services/exportService";
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
  const exportReport = useExportDailyReport();
  const [mode, setMode] = useState<"view" | "reject" | "copy">("view");
  const [confirm, setConfirm] = useState<DailyAction | "delete" | null>(null);
  const p = detail.data ?? plan;
  // Galat tindakan lama (mis. "Jadwal belum berisi pekerjaan") hanya tampil selama isi jadwal belum berubah.
  const [errorRaw, setErrorRaw] = useState<{ msg: string; key: string } | null>(null);
  const snapshot = `${p.item_count}|${p.status}`;
  const error = errorRaw && errorRaw.key === snapshot ? errorRaw.msg : null;
  const setError = (msg: string | null) => setErrorRaw(msg ? { msg, key: snapshot } : null);
  const rejectForm = useDirtyForm();
  const copyForm = useDirtyForm();
  const formDirty = (mode === "reject" && rejectForm.dirty) || (mode === "copy" && copyForm.dirty);
  // Pindah mode membuang isian formulir kecil dan keadaan kotornya.
  const enterMode = (next: "view" | "reject" | "copy") => {
    rejectForm.reset();
    copyForm.reset();
    setMode(next);
  };
  // Tombol persetujuan hanya untuk PM/OM divisi jadwal (can_manage, dihitung API); ketua & anggota tidak melihatnya.
  const manages = !!p.can_manage;
  const editable = manages && (p.status === "DRAFT" || p.status === "SUBMITTED");
  const deletable = manages && (p.status === "DRAFT" || p.status === "SUBMITTED" || p.status === "APPROVED");

  const run = async (fn: () => Promise<unknown>, done: string, close = false) => {
    setError(null);
    try {
      await fn();
      toast.success(done);
      if (close) onClose();
      else enterMode("view");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };
  const act = (action: DailyAction) =>
    run(() => transition.mutateAsync({ id: p.daily_plan_id, action }), `Jadwal: ${ACTION_LABEL[action].toLowerCase()}.`);

  const actions: DailyAction[] = [
    // PM/OM menyetujui draf miliknya langsung (satu langkah di API); tidak ada tombol "Ajukan ke PM" bagi PM/OM.
    ...(manages && (p.status === "DRAFT" || p.status === "SUBMITTED") ? (["approve"] as const) : []),
    ...(isLeader && p.status === "APPROVED" ? (["start"] as const) : []),
    ...((isLeader || manages) && p.status === "ONGOING" ? (["complete"] as const) : []),
  ];

  const pct = displayPct(p);
  const state = WORK_STATE[workState(p, wibDate())];

  return (
    <VmsDialog open title={`${p.team_name} · ${formatDate(p.work_date)}`} onClose={onClose} dirty={formDirty}>
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
            Jam kerja: {(p.clock_in_time ?? "08:00").slice(0, 5)}–{(p.clock_out_time ?? "17:00").slice(0, 5)}
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
            {...rejectForm.formProps}
            className="space-y-2"
            noValidate
            onSubmit={(e) => {
              e.preventDefault();
              const reason = String(new FormData(e.currentTarget).get("reason") ?? "").trim();
              if (reason.length < 3) return setError("Alasan minimal 3 huruf.");
              void run(() => reject.mutateAsync({ id: p.daily_plan_id, reason }), "Jadwal dikembalikan ke draf.");
            }}
          >
            <TextAreaField name="reason" label="Alasan dikembalikan" />
            <div className="flex gap-2">
              <ActionButton type="submit" size="sm" disabled={reject.isPending}>Kembalikan ke draf</ActionButton>
              <DialogCancelButton onCancel={() => enterMode("view")} disabled={reject.isPending} />
            </div>
          </FormBlock>
        )}
        {mode === "copy" && (
          <FormBlock
            {...copyForm.formProps}
            className="space-y-2"
            noValidate
            onSubmit={(e) => {
              e.preventDefault();
              // Ketikan manual dd/mm/yyyy (atau yyyy-mm-dd); tidak bergantung pada pemilih tanggal peramban.
              const until = parseTanggalInput(String(new FormData(e.currentTarget).get("until") ?? ""));
              if (!until) return setError("Tanggal tidak valid. Tulis dengan format dd/mm/yyyy, misalnya 01/11/2026.");
              // Salin boleh maju atau mundur dari tanggal jadwal ini (tanggal sebelum hari ini ditolak API).
              const dates: string[] = [];
              const [from, to] = until >= p.work_date ? [addDays(p.work_date, 1), until] : [until, addDays(p.work_date, -1)];
              for (let d = from; d <= to; d = addDays(d, 1)) dates.push(d);
              if (!dates.length) return setError("Pilih tanggal lain selain tanggal jadwal ini.");
              void run(() => copy.mutateAsync({ id: p.daily_plan_id, work_dates: dates }), `${dates.length} jadwal draf dibuat.`, true);
            }}
          >
            <TextField
              name="until"
              label="Salin setiap hari sampai tanggal"
              placeholder="dd/mm/yyyy"
              inputMode="numeric"
              hint="Contoh: 01/11/2026"
            />
            <div className="flex gap-2">
              <ActionButton type="submit" size="sm" disabled={copy.isPending}>Salin</ActionButton>
              <DialogCancelButton onCancel={() => enterMode("view")} disabled={copy.isPending} />
            </div>
          </FormBlock>
        )}

        <div className="flex flex-wrap gap-2 border-t border-line pt-3">
          {actions.map((a) => {
            // API menolak pengajuan/persetujuan jadwal tanpa item; tombolnya dinonaktifkan dengan petunjuk.
            const kosong = p.item_count === 0 && (a === "submit" || a === "approve");
            return (
              <ActionButton key={a} size="sm" disabled={transition.isPending || kosong} onClick={() => setConfirm(a)}>
                {ACTION_LABEL[a]}
              </ActionButton>
            );
          })}
          {p.item_count === 0 && actions.some((a) => a === "submit" || a === "approve") && (
            <TextBlock as="span" className="basis-full text-xs text-mist">
              Tambahkan minimal satu pekerjaan sebelum diajukan atau disetujui.
            </TextBlock>
          )}
          {manages && mode === "view" && (p.status === "SUBMITTED" || p.status === "APPROVED") && (
            <ActionButton size="sm" variant="outline" onClick={() => enterMode("reject")}>Kembalikan ke draf</ActionButton>
          )}
          {(canPlan || isLeader) && (
            <ActionButton
              size="sm"
              variant="outline"
              disabled={exportReport.isPending}
              onClick={() =>
                exportReport.mutate(
                  { daily_plan_id: p.daily_plan_id },
                  {
                    onSuccess: () => toast.success("Laporan harian siap diunduh."),
                    onError: (err) => toast.error(errorMessage(err)),
                  },
                )
              }
            >
              Cetak laporan harian (.docx)
            </ActionButton>
          )}
          {editable && <ActionButton size="sm" variant="outline" onClick={onEdit}>Ubah</ActionButton>}
          {manages && <ActionButton size="sm" variant="outline" onClick={() => enterMode("copy")}>Salin ke hari lain</ActionButton>}
          {/* F10: hapus (lunak) untuk draf, diajukan, dan disetujui yang belum dimulai; API menolak bila sudah dipakai. */}
          {deletable && (
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
