/**
 * web/src/components/organisms/work-plans/DailyScheduleSlotsCards.tsx
 * Komponen kartu multi-slot jadwal harian tugas rencana kerja (work_plan_item).
 * Menampilkan rincian slot jam kerja, SOP foto, order klien, progres capaian,
 * serta tombol aksi pelaporan progres, pengajuan rollover, dan PM override.
 * Sesuai aturan Atomic Design (docs/33 §2): Menggunakan molekul tanpa impor atom/lucide langsung.
 */

import React, { useState } from "react";
import { useSession } from "@/stores/sessionStore";
import { ActionButton } from "@/components/molecules/ActionButton";
import { PlainAction } from "@/components/molecules/PlainAction";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FormBlock, ControlLabel, ControlInput, ControlTextarea } from "@/components/molecules/FormBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import {
  Building,
  CalendarClock,
  Camera,
  CheckCircle2,
  Clock,
  FileCheck2,
  GitFork,
  Layers,
  Lock,
  MapPin,
  Send,
  Trash2,
  Users,
} from "@/components/molecules/Glyphs";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import {
  requestItemRollover,
  updateItemProgress,
  type ItemScheduleSlot,
} from "@/services/planItemService";
import {
  useDeletePlanItemV2,
  useWorkPlanFormOptionsV2,
} from "@/services/workPlanV2Service";
import type { PlanItemV2Value } from "@/schemas/workPlanV2Schema";
import { RescheduleTaskModal } from "./RescheduleTaskModal";
import { WorkTypeSopModal } from "./WorkTypeSopModal";
import { PlanItemFormDialog } from "./PlanItemFormDialog";
import { TaskChainCompletionDialog } from "./TaskChainCompletionDialog";
import { PlanItemRolloverDialog } from "./PlanItemRolloverDialog";

interface DailyScheduleSlotsCardsProps {
  slots: ItemScheduleSlot[];
  currentDate: string;
  dailyPlanId: string;
  availableDays?: Array<{ daily_plan_id: string; work_date: string; site_name?: string }>;
  onRefresh?: () => void;
}

const PHASE_LABELS: Record<string, { label: string; color: string }> = {
  SURVEY: { label: "Survei", color: "bg-amber-950/80 text-amber-300 border-amber-700" },
  PREPARATION: { label: "Persiapan & Galian", color: "bg-cyan-950/80 text-cyan-300 border-cyan-700" },
  MAIN_INSTALLATION: { label: "Instalasi Utama", color: "bg-blue-950/80 text-blue-300 border-blue-700" },
  TESTING_COMMISSIONING: { label: "Testing & Komisi", color: "bg-purple-950/80 text-purple-300 border-purple-700" },
  FINISHING: { label: "Finishing", color: "bg-teal-950/80 text-teal-300 border-teal-700" },
};

export const DailyScheduleSlotsCards: React.FC<DailyScheduleSlotsCardsProps> = ({
  slots = [],
  currentDate,
  dailyPlanId,
  availableDays = [],
  onRefresh,
}) => {
  const { me } = useSession();
  const qc = useQueryClient();

  const [selectedSlotForReschedule, setSelectedSlotForReschedule] = useState<ItemScheduleSlot | null>(null);
  const [sopModalData, setSopModalData] = useState<{ id: string; name: string } | null>(null);

  // State Dialog Update Progress
  const [progressSlot, setProgressSlot] = useState<ItemScheduleSlot | null>(null);
  const [completedQty, setCompletedQty] = useState<number>(0);
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [updatingProgress, setUpdatingProgress] = useState<boolean>(false);

  // State Dialog Rollover
  const [rolloverSlot, setRolloverSlot] = useState<ItemScheduleSlot | null>(null);
  const [rolloverReason, setRolloverReason] = useState<string>("");
  const [submittingRollover, setSubmittingRollover] = useState<boolean>(false);

  // State Dialog Task Chain & Direct PM Rollover
  const [chainDialogItemId, setChainDialogItemId] = useState<string | null>(null);
  const [rolloverDialogItem, setRolloverDialogItem] = useState<ItemScheduleSlot | null>(null);

  // State Dialog Edit Item Slot & Delete
  const [editingSlot, setEditingSlot] = useState<ItemScheduleSlot | null>(null);
  const deleteItemMut = useDeletePlanItemV2();
  const optionsQuery = useWorkPlanFormOptionsV2();

  const isPmOrHigher =
    me?.role === "PROJECT_MANAGER" ||
    me?.role === "OPERATIONAL_MANAGER" ||
    me?.role === "SUPER_ADMIN" ||
    me?.role === "PM" ||
    me?.role === "ADMIN" ||
    Boolean(me?.permissions.includes("create:plan"));

  const [slotToDelete, setSlotToDelete] = useState<string | null>(null);

  const handleConfirmDeleteSlot = async () => {
    if (!slotToDelete) return;
    try {
      await deleteItemMut.mutateAsync({ id: slotToDelete, dailyPlanId });
      toast.success("Butir tugas berhasil dihapus!");
      qc.invalidateQueries({ queryKey: ["daily-schedule-detail", dailyPlanId] });
      qc.invalidateQueries({ queryKey: ["plan-days"] });
      onRefresh?.();
      setSlotToDelete(null);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Gagal menghapus tugas.");
    }
  };

  const openProgressModal = (slot: ItemScheduleSlot) => {
    setProgressSlot(slot);
    setCompletedQty(slot.completed_qty || 0);
    setProgressPercent(slot.progress_percent || 0);
  };

  const handleSaveProgress = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!progressSlot) return;

    setUpdatingProgress(true);
    try {
      await updateItemProgress(progressSlot.item_id, {
        completed_qty: Number(completedQty),
        progress_percent: Number(progressPercent),
      });
      toast.success("Capaian progres tugas berhasil diperbarui!");
      setProgressSlot(null);
      qc.invalidateQueries({ queryKey: ["daily-schedule-detail", dailyPlanId] });
      qc.invalidateQueries({ queryKey: ["plan-days"] });
      onRefresh?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal memperbarui progres.";
      toast.error(msg);
    } finally {
      setUpdatingProgress(false);
    }
  };

  const openRolloverModal = (slot: ItemScheduleSlot) => {
    setRolloverSlot(slot);
    setRolloverReason("");
  };

  const handleSubmitRollover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rolloverSlot || !rolloverReason.trim()) {
      toast.error("Alasan kendala lapangan wajib diisi.");
      return;
    }

    setSubmittingRollover(true);
    try {
      await requestItemRollover(rolloverSlot.item_id, {
        delay_reason: rolloverReason.trim(),
      });
      toast.success("Pengajuan rollover tugas berhasil dikirimkan ke PM!");
      setRolloverSlot(null);
      qc.invalidateQueries({ queryKey: ["daily-schedule-detail", dailyPlanId] });
      qc.invalidateQueries({ queryKey: ["plan-days"] });
      onRefresh?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal mengajukan rollover.";
      toast.error(msg);
    } finally {
      setSubmittingRollover(false);
    }
  };

  if (!slots || slots.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-xl text-slate-400">
        <Clock className="w-10 h-10 text-slate-600 mx-auto mb-2" />
        <TextBlock className="text-sm font-medium">Belum ada slot penugasan untuk hari ini.</TextBlock>
        <TextBlock className="text-xs text-slate-500 mt-1">
          Gunakan tombol Tambah Tugas pada Rencana Kerja untuk mengisi jadwal multi-slot.
        </TextBlock>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4">
        {slots.map((slot, index) => {
          const isDone = slot.status === "DONE" || slot.progress_percent >= 100;
          const isRolloverPending = slot.status === "PENDING_ROLLOVER";

          return (
            <div
              key={slot.item_id}
              className={`rounded-xl border p-4 transition-all duration-200 bg-slate-900/90 shadow-md ${
                isDone
                  ? "border-emerald-700/50 bg-emerald-950/10"
                  : isRolloverPending
                  ? "border-amber-700/50 bg-amber-950/10"
                  : "border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                {/* Header Slot: Jam & Judul */}
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <TextBlock as="span" className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-950/80 text-sky-400 border border-sky-800/60 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <TextBlock as="span">
                        Slot #{index + 1} ({slot.start_time?.slice(0, 5) || "08:00"} - {slot.end_time?.slice(0, 5) || "12:00"})
                      </TextBlock>
                    </TextBlock>

                    <TextBlock
                      as="span"
                      className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                        isDone
                          ? "bg-emerald-950 text-emerald-400 border-emerald-800"
                          : isRolloverPending
                          ? "bg-amber-950 text-amber-400 border-amber-800 animate-pulse"
                          : slot.status === "SHIFTED_DAY"
                          ? "bg-amber-950/90 text-amber-300 border-amber-700"
                          : slot.status === "ALLOCATED_NEXT_WEEK"
                          ? "bg-sky-950/90 text-sky-300 border-sky-700"
                          : "bg-slate-800 text-slate-300 border-slate-700"
                      }`}
                    >
                      {slot.status === "SHIFTED_DAY"
                        ? "Digeser ke Hari Lain"
                        : slot.status === "ALLOCATED_NEXT_WEEK"
                        ? "Dialokasikan ke Minggu Depan"
                        : slot.status}
                    </TextBlock>

                    {/* Badge Tahap Pekerjaan Multi-Minggu */}
                    {slot.task_phase && (
                      <TextBlock
                        as="span"
                        className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                          PHASE_LABELS[slot.task_phase]?.color || "bg-slate-800 text-slate-300 border-slate-700"
                        }`}
                      >
                        {PHASE_LABELS[slot.task_phase]?.label || slot.task_phase}
                      </TextBlock>
                    )}

                    {/* Badge Prasyarat Terkunci */}
                    {slot.depends_on_item_id && (
                      <TextBlock as="span" className="text-[11px] font-medium px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-700 flex items-center gap-1 font-mono">
                        <Lock className="w-3 h-3 text-amber-400" />
                        <TextBlock as="span">Ada Prasyarat</TextBlock>
                      </TextBlock>
                    )}

                    {/* Badge Deliverable Utama (BAST) vs Pendukung */}
                    {slot.is_main_deliverable === false ? (
                      <TextBlock as="span" className="text-[11px] font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        Pendukung (Non-BAST)
                      </TextBlock>
                    ) : (
                      <TextBlock as="span" className="text-[11px] font-medium px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-700">
                        Deliverable Utama (BAST)
                      </TextBlock>
                    )}

                    {/* Badge Foto Realisasi */}
                    {Boolean(slot.realization_photos_json && slot.realization_photos_json.length > 0) && (
                      <TextBlock as="span" className="text-[11px] font-medium px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-700 flex items-center gap-1 font-mono">
                        <Camera className="w-3 h-3 text-indigo-400" />
                        <TextBlock as="span">{slot.realization_photos_json!.length} Foto</TextBlock>
                      </TextBlock>
                    )}

                    {slot.origin_item_id && (
                      <TextBlock as="span" className="text-[11px] font-medium px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800 flex items-center gap-1">
                        <GitFork className="w-3 h-3 text-purple-400" />
                        <TextBlock as="span">Tugas Lanjutan</TextBlock>
                      </TextBlock>
                    )}

                    {slot.completion_id && (
                      <TextBlock as="span" className="text-[11px] font-medium px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700 flex items-center gap-1 font-mono">
                        <FileCheck2 className="w-3 h-3 text-emerald-400" />
                        <TextBlock as="span">BA Terbit</TextBlock>
                      </TextBlock>
                    )}

                    {slot.work_type && (
                      <PlainAction
                        type="button"
                        onClick={() =>
                          setSopModalData({
                            id: slot.work_type!.work_type_id,
                            name: slot.work_type!.name,
                          })
                        }
                        className="text-[11px] font-medium px-2 py-0.5 rounded bg-violet-950/70 text-violet-300 border border-violet-800/60 hover:bg-violet-900 flex items-center gap-1 transition cursor-pointer"
                      >
                        <Camera className="w-3 h-3 text-violet-400" />
                        <TextBlock as="span">SOP: {slot.work_type.name}</TextBlock>
                      </PlainAction>
                    )}
                  </div>

                  <TextBlock as="h3" className="text-base font-semibold text-white pt-1">
                    {slot.title}
                  </TextBlock>

                  {/* Lokasi Site */}
                  {slot.location_name && (
                    <TextBlock className="text-xs text-slate-400 flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                      <TextBlock as="span">{slot.location_name}</TextBlock>
                    </TextBlock>
                  )}
                </div>

                {/* Target & Realisasi Capaian */}
                <div className="text-right space-y-1 min-w-[130px]">
                  <div className="text-xs text-slate-400">
                    <TextBlock as="span">Progres: </TextBlock>
                    <TextBlock as="span" className="font-semibold text-white">{slot.progress_percent || 0}%</TextBlock>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
                    <div
                      className={`h-full transition-all duration-300 ${
                        isDone ? "bg-emerald-500" : "bg-sky-500"
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, slot.progress_percent || 0))}%` }}
                    />
                  </div>
                  <div className="text-[11px] text-slate-400">
                    <TextBlock as="span">{slot.completed_qty || 0} / {slot.target_qty || 0} unit</TextBlock>
                  </div>
                </div>
              </div>

              {/* Order Klien Jika Terhubung */}
              {slot.work_completion_order && (
                <div className="mt-3 p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/90 text-xs flex flex-wrap items-center justify-between gap-2 text-slate-300">
                  <div className="flex items-center gap-2">
                    <Building className="w-4 h-4 text-emerald-400 shrink-0" />
                    <div>
                      <TextBlock as="span" className="font-medium text-white">
                        {slot.work_completion_order.client_name}
                      </TextBlock>
                      <TextBlock as="span" className="text-slate-500 mx-1.5">•</TextBlock>
                      <TextBlock as="span">{slot.work_completion_order.project_title}</TextBlock>
                    </div>
                  </div>
                  <TextBlock as="span" className="text-[11px] font-mono text-sky-400 bg-sky-950/60 px-2 py-0.5 rounded border border-sky-800/40">
                    {slot.work_completion_order.order_number}
                  </TextBlock>
                </div>
              )}

              {/* Action Buttons Bar */}
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 text-xs text-slate-400">
                  <Users className="w-3.5 h-3.5 text-sky-400" />
                  <TextBlock as="span">
                    {slot.assigned_employee_ids?.length || 0} Teknisi Ditugaskan
                  </TextBlock>
                </div>

                <div className="flex items-center gap-2">
                  {/* Tombol Rantai Tugas & Berita Acara */}
                  <ActionButton
                    size="sm"
                    variant="outline"
                    onClick={() => setChainDialogItemId(slot.item_id)}
                    className="text-xs bg-slate-800 hover:bg-slate-700 text-sky-300 border-slate-700 h-8 gap-1"
                    title="Lihat Silsilah Rantai Tugas & Terbitkan Berita Acara"
                  >
                    <Layers className="w-3.5 h-3.5 text-sky-400" />
                    <TextBlock as="span">Rantai Tugas</TextBlock>
                  </ActionButton>

                  {/* Tombol Update Progres */}
                  <ActionButton
                    size="sm"
                    variant="outline"
                    onClick={() => openProgressModal(slot)}
                    className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 h-8 gap-1"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <TextBlock as="span">Update Progres</TextBlock>
                  </ActionButton>

                  {/* Tombol Rollover Tugas (Langsung untuk PM, atau Pengajuan untuk Teknisi/Leader) */}
                  {!isDone && (
                    <ActionButton
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        isPmOrHigher
                          ? setRolloverDialogItem(slot)
                          : openRolloverModal(slot)
                      }
                      className="text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 border-slate-700 h-8 gap-1"
                      title={isPmOrHigher ? "Eksekusi Rollover ke Hari Kerja Lain" : "Ajukan Rollover ke PM"}
                    >
                      <Send className="w-3.5 h-3.5 text-amber-400" />
                      <TextBlock as="span">{isPmOrHigher ? "Rollover Tugas" : "Ajukan Rollover"}</TextBlock>
                    </ActionButton>
                  )}

                  {/* Tombol PM Override Reschedule */}
                  {isPmOrHigher && (
                    <>
                      <ActionButton
                        size="sm"
                        variant="outline"
                        onClick={() => setEditingSlot(slot)}
                        className="text-xs bg-slate-800 hover:bg-slate-700 text-sky-300 border-slate-700 h-8 gap-1"
                        title="Ubah Rincian Tugas"
                      >
                        <TextBlock as="span">✏️ Edit</TextBlock>
                      </ActionButton>
                      <ActionButton
                        size="sm"
                        variant="outline"
                        onClick={() => setSlotToDelete(slot.item_id)}
                        className="text-xs bg-slate-800 hover:bg-red-950/80 text-rose-300 border-slate-700 h-8 gap-1"
                        title="Hapus Tugas"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                        <TextBlock as="span">Hapus</TextBlock>
                      </ActionButton>
                      <ActionButton
                        size="sm"
                        onClick={() => setSelectedSlotForReschedule(slot)}
                        className="text-xs bg-amber-600 hover:bg-amber-500 text-white font-medium h-8 gap-1 shadow"
                      >
                        <CalendarClock className="w-3.5 h-3.5" />
                        <TextBlock as="span">PM Reschedule</TextBlock>
                      </ActionButton>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal Reschedule PM */}
      {selectedSlotForReschedule && (
        <RescheduleTaskModal
          isOpen={Boolean(selectedSlotForReschedule)}
          onClose={() => setSelectedSlotForReschedule(null)}
          item={selectedSlotForReschedule}
          currentDate={currentDate}
          availableDays={availableDays}
          onSuccess={() => {
            qc.invalidateQueries({ queryKey: ["daily-schedule-detail", dailyPlanId] });
            onRefresh?.();
          }}
        />
      )}

      {/* Modal SOP Foto Preview */}
      {sopModalData && (
        <WorkTypeSopModal
          workTypeId={sopModalData.id}
          workTypeName={sopModalData.name}
          onClose={() => setSopModalData(null)}
        />
      )}

      {/* Dialog Update Progres */}
      {progressSlot && (
        <VmsDialog
          open={Boolean(progressSlot)}
          onClose={() => setProgressSlot(null)}
          title="Update Progres Lapangan"
        >
          <div className="space-y-4 pt-1 text-xs">
            <TextBlock className="text-mist truncate">
              Tugas: {progressSlot.title}
            </TextBlock>

            <FormBlock onSubmit={handleSaveProgress} className="space-y-4">
              <div className="space-y-1.5">
                <ControlLabel className="text-xs font-medium">
                  Target Total ({progressSlot.target_qty || 0} unit)
                </ControlLabel>
                <TextBlock className="text-xs text-mist">
                  Masukkan jumlah unit aktual yang telah selesai dipasang/disurvei:
                </TextBlock>
                <ControlInput
                  type="number"
                  step="0.01"
                  min="0"
                  max={progressSlot.target_qty ? progressSlot.target_qty * 2 : 1000}
                  value={completedQty}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value) || 0;
                    setCompletedQty(val);
                    if (progressSlot.target_qty && progressSlot.target_qty > 0) {
                      const pct = Math.min(100, Math.round((val / progressSlot.target_qty) * 100));
                      setProgressPercent(pct);
                    }
                  }}
                  className="w-full text-xs"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <ControlLabel className="text-xs font-medium">
                  Persentase Progres (%)
                </ControlLabel>
                <ControlInput
                  type="number"
                  min="0"
                  max="100"
                  value={progressPercent}
                  onChange={(e) => setProgressPercent(parseInt(e.target.value, 10) || 0)}
                  className="w-full text-xs"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-line">
                <ActionButton
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setProgressSlot(null)}
                  disabled={updatingProgress}
                >
                  Batal
                </ActionButton>
                <ActionButton
                  type="submit"
                  size="sm"
                  variant="default"
                  disabled={updatingProgress}
                >
                  {updatingProgress ? "Menyimpan..." : "Simpan Capaian"}
                </ActionButton>
              </div>
            </FormBlock>
          </div>
        </VmsDialog>
      )}

      {/* Dialog Ajukan Rollover */}
      {rolloverSlot && (
        <VmsDialog
          open={Boolean(rolloverSlot)}
          onClose={() => setRolloverSlot(null)}
          title="Ajukan Rollover Tugas"
        >
          <div className="space-y-4 pt-1 text-xs">
            <TextBlock className="text-mist truncate">
              Tugas: {rolloverSlot.title}
            </TextBlock>

            <FormBlock onSubmit={handleSubmitRollover} className="space-y-4">
              <div className="p-3 bg-amber-950/40 border border-amber-800/60 rounded-panel text-xs text-amber-200 space-y-1">
                <TextBlock as="p" className="font-medium">Ketentuan Rollover:</TextBlock>
                <TextBlock as="p" className="text-[11px] text-slate-300">
                  Tugas yang belum rampung hari ini akan dialihkan ke status <TextBlock as="span" className="font-mono text-amber-300">PENDING_ROLLOVER</TextBlock> dan menunggu verifikasi Project Manager (PM) untuk dijadwalkan ke hari kerja berikutnya.
                </TextBlock>
              </div>

              <div className="space-y-1.5">
                <ControlLabel className="text-xs font-medium">
                  Alasan Kendala Lapangan (Wajib)
                </ControlLabel>
                <ControlTextarea
                  value={rolloverReason}
                  onChange={(e) => setRolloverReason(e.target.value)}
                  placeholder="Contoh: Hujan lebat disertai petir di lokasi tower BTS, instalasi kabel FO dihentikan demi keselamatan K3..."
                  rows={3}
                  className="w-full text-xs resize-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-line">
                <ActionButton
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setRolloverSlot(null)}
                  disabled={submittingRollover}
                >
                  Batal
                </ActionButton>
                <ActionButton
                  type="submit"
                  size="sm"
                  variant="default"
                  disabled={submittingRollover}
                >
                  {submittingRollover ? "Mengirim..." : "Kirimkan ke PM"}
                </ActionButton>
              </div>
            </FormBlock>
          </div>
        </VmsDialog>
      )}

      {/* Dialog Edit Slot Tugas */}
      {editingSlot && (
        <PlanItemFormDialog
          open={Boolean(editingSlot)}
          onClose={() => setEditingSlot(null)}
          dailyPlanId={dailyPlanId}
          initialData={{
            item_id: editingSlot.item_id,
            title: editingSlot.title,
            work_type_id: editingSlot.work_type?.work_type_id,
            completion_id: editingSlot.work_completion_order?.completion_id,
            target_qty: editingSlot.target_qty,
            completed_qty: editingSlot.completed_qty,
            progress_percent: editingSlot.progress_percent,
            start_time: editingSlot.start_time || undefined,
            end_time: editingSlot.end_time || undefined,
            location_name: editingSlot.location_name || undefined,
            assigned_employee_ids: editingSlot.assigned_employee_ids,
            status: editingSlot.status as PlanItemV2Value["status"],
          }}
          workTypes={optionsQuery.data?.work_types || []}
          completions={optionsQuery.data?.work_completions || []}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ["daily-schedule-detail", dailyPlanId] });
            onRefresh?.();
          }}
        />
      )}

      {/* Dialog Silsilah Rantai Tugas & Work Completion */}
      <TaskChainCompletionDialog
        itemId={chainDialogItemId}
        isOpen={Boolean(chainDialogItemId)}
        onClose={() => setChainDialogItemId(null)}
        onSuccess={() => {
          qc.invalidateQueries({ queryKey: ["daily-schedule-detail", dailyPlanId] });
          qc.invalidateQueries({ queryKey: ["plan-days"] });
          onRefresh?.();
        }}
      />

      {/* Dialog Eksekusi Rollover PM */}
      <PlanItemRolloverDialog
        isOpen={Boolean(rolloverDialogItem)}
        onClose={() => setRolloverDialogItem(null)}
        item={rolloverDialogItem}
        dailyPlanId={dailyPlanId}
        currentDate={currentDate}
        availableDays={availableDays}
        onSuccess={() => {
          qc.invalidateQueries({ queryKey: ["daily-schedule-detail", dailyPlanId] });
          qc.invalidateQueries({ queryKey: ["plan-days"] });
          onRefresh?.();
        }}
      />
      {/* Dialog Konfirmasi Hapus Tugas */}
      <VmsDialog
        open={Boolean(slotToDelete)}
        onClose={() => setSlotToDelete(null)}
        title="Hapus Butir Tugas"
      >
        <div className="space-y-4">
          <TextBlock className="text-sm text-slate-300">
            Apakah Anda yakin ingin menghapus butir tugas slot ini? Tindakan ini tidak dapat dibatalkan.
          </TextBlock>
          <div className="flex justify-end gap-2 pt-2">
            <ActionButton
              type="button"
              variant="outline"
              onClick={() => setSlotToDelete(null)}
            >
              Batal
            </ActionButton>
            <ActionButton
              type="button"
              variant="destructive"
              onClick={handleConfirmDeleteSlot}
              disabled={deleteItemMut.isPending}
            >
              {deleteItemMut.isPending ? "Menghapus..." : "Ya, Hapus"}
            </ActionButton>
          </div>
        </div>
      </VmsDialog>
    </div>
  );
};
