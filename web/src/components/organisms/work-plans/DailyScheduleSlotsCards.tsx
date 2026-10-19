/**
 * web/src/components/organisms/work-plans/DailyScheduleSlotsCards.tsx
 * Komponen kartu multi-slot jadwal harian tugas rencana kerja (work_plan_item).
 * Menampilkan rincian slot jam kerja, SOP foto, order klien, progres capaian,
 * serta tombol aksi pelaporan progres, pengajuan rollover, dan PM override.
 */

import React, { useState } from "react";
import { useSession } from "@/stores/sessionStore";
import { Button } from "@/components/atoms/Button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/atoms/Dialog";
import {
  Building,
  CalendarClock,
  Camera,
  CheckCircle2,
  Clock,
  MapPin,
  Send,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import {
  requestItemRollover,
  updateItemProgress,
  type ItemScheduleSlot,
} from "@/services/planItemService";
import { RescheduleTaskModal } from "./RescheduleTaskModal";
import { WorkTypeSopModal } from "./WorkTypeSopModal";

interface DailyScheduleSlotsCardsProps {
  slots: ItemScheduleSlot[];
  currentDate: string;
  dailyPlanId: string;
  availableDays?: Array<{ daily_plan_id: string; work_date: string; site_name?: string }>;
  onRefresh?: () => void;
}

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

  const isPmOrHigher =
    me?.role === "PROJECT_MANAGER" ||
    me?.role === "OPERATIONAL_MANAGER" ||
    me?.role === "SUPER_ADMIN" ||
    me?.role === "PM" ||
    me?.role === "ADMIN" ||
    !!me?.permissions.includes("create:plan");

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
        <p className="text-sm font-medium">Belum ada slot penugasan untuk hari ini.</p>
        <p className="text-xs text-slate-500 mt-1">
          Gunakan tombol Tambah Tugas pada Rencana Kerja untuk mengisi jadwal multi-slot.
        </p>
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
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-950/80 text-sky-400 border border-sky-800/60 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Slot #{index + 1} ({slot.start_time?.slice(0, 5) || "08:00"} - {slot.end_time?.slice(0, 5) || "12:00"})
                    </span>

                    <span
                      className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                        isDone
                          ? "bg-emerald-950 text-emerald-400 border-emerald-800"
                          : isRolloverPending
                          ? "bg-amber-950 text-amber-400 border-amber-800 animate-pulse"
                          : "bg-slate-800 text-slate-300 border-slate-700"
                      }`}
                    >
                      {slot.status}
                    </span>

                    {slot.work_type && (
                      <button
                        type="button"
                        onClick={() =>
                          setSopModalData({
                            id: slot.work_type!.work_type_id,
                            name: slot.work_type!.name,
                          })
                        }
                        className="text-[11px] font-medium px-2 py-0.5 rounded bg-violet-950/70 text-violet-300 border border-violet-800/60 hover:bg-violet-900 flex items-center gap-1 transition"
                      >
                        <Camera className="w-3 h-3 text-violet-400" />
                        SOP: {slot.work_type.name}
                      </button>
                    )}
                  </div>

                  <h4 className="text-base font-semibold text-white pt-1">
                    {slot.title}
                  </h4>

                  {/* Lokasi Site */}
                  {slot.location_name && (
                    <p className="text-xs text-slate-400 flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                      <span>{slot.location_name}</span>
                    </p>
                  )}
                </div>

                {/* Target & Realisasi Capaian */}
                <div className="text-right space-y-1 min-w-[130px]">
                  <div className="text-xs text-slate-400">
                    Progres: <span className="font-semibold text-white">{slot.progress_percent || 0}%</span>
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
                    {slot.completed_qty || 0} / {slot.target_qty || 0} unit
                  </div>
                </div>
              </div>

              {/* Order Klien Jika Terhubung */}
              {slot.work_completion_order && (
                <div className="mt-3 p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/90 text-xs flex flex-wrap items-center justify-between gap-2 text-slate-300">
                  <div className="flex items-center gap-2">
                    <Building className="w-4 h-4 text-emerald-400 shrink-0" />
                    <div>
                      <span className="font-medium text-white">
                        {slot.work_completion_order.client_name}
                      </span>
                      <span className="text-slate-500 mx-1.5">•</span>
                      <span>{slot.work_completion_order.project_title}</span>
                    </div>
                  </div>
                  <span className="text-[11px] font-mono text-sky-400 bg-sky-950/60 px-2 py-0.5 rounded border border-sky-800/40">
                    {slot.work_completion_order.order_number}
                  </span>
                </div>
              )}

              {/* Action Buttons Bar */}
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 text-xs text-slate-400">
                  <Users className="w-3.5 h-3.5 text-sky-400" />
                  <span>
                    {slot.assigned_employee_ids?.length || 0} Teknisi Ditugaskan
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {/* Tombol Update Progres */}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => openProgressModal(slot)}
                    className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 h-8 gap-1"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    Update Progres
                  </Button>

                  {/* Tombol Ajukan Rollover (untuk Leader bila belum selesai) */}
                  {!isDone && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => openRolloverModal(slot)}
                      className="text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 border-slate-700 h-8 gap-1"
                    >
                      <Send className="w-3.5 h-3.5 text-amber-400" />
                      Ajukan Rollover
                    </Button>
                  )}

                  {/* Tombol PM Override Reschedule */}
                  {isPmOrHigher && (
                    <Button
                      size="sm"
                      onClick={() => setSelectedSlotForReschedule(slot)}
                      className="text-xs bg-amber-600 hover:bg-amber-500 text-white font-medium h-8 gap-1 shadow"
                    >
                      <CalendarClock className="w-3.5 h-3.5" />
                      PM Reschedule
                    </Button>
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
          isOpen={!!selectedSlotForReschedule}
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
        <Dialog open={!!progressSlot} onOpenChange={(open) => !open && setProgressSlot(null)}>
          <DialogContent className="max-w-md p-6 bg-slate-900 border-slate-800 text-white shadow-2xl rounded-xl">
            <DialogHeader className="space-y-1">
              <DialogTitle className="text-base font-semibold text-white">
                Update Progres Lapangan
              </DialogTitle>
              <p className="text-xs text-slate-400 truncate">
                Tugas: {progressSlot.title}
              </p>
            </DialogHeader>

            <form onSubmit={handleSaveProgress} className="space-y-4 pt-2">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">
                  Target Total ({progressSlot.target_qty || 0} unit)
                </label>
                <div className="text-xs text-slate-400">
                  Masukkan jumlah unit aktual yang telah selesai dipasang/disurvei:
                </div>
                <input
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
                  className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">
                  Persentase Progres (%)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={progressPercent}
                  onChange={(e) => setProgressPercent(parseInt(e.target.value, 10) || 0)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setProgressSlot(null)}
                  disabled={updatingProgress}
                  className="text-slate-400 hover:text-white text-xs h-9"
                >
                  Batal
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={updatingProgress}
                  className="bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs h-9 shadow"
                >
                  {updatingProgress ? "Menyimpan..." : "Simpan Capaian"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      )}

      {/* Dialog Ajukan Rollover */}
      {rolloverSlot && (
        <Dialog open={!!rolloverSlot} onOpenChange={(open) => !open && setRolloverSlot(null)}>
          <DialogContent className="max-w-md p-6 bg-slate-900 border-slate-800 text-white shadow-2xl rounded-xl">
            <DialogHeader className="space-y-1">
              <div className="flex items-center gap-2">
                <Send className="w-5 h-5 text-amber-400" />
                <DialogTitle className="text-base font-semibold text-white">
                  Ajukan Rollover Tugas
                </DialogTitle>
              </div>
              <p className="text-xs text-slate-400 truncate">
                Tugas: {rolloverSlot.title}
              </p>
            </DialogHeader>

            <form onSubmit={handleSubmitRollover} className="space-y-4 pt-2">
              <div className="p-3 bg-amber-950/40 border border-amber-800/60 rounded-lg text-xs text-amber-200 space-y-1">
                <p className="font-medium">Ketentuan Rollover:</p>
                <p className="text-[11px] text-slate-300">
                  Tugas yang belum rampung hari ini akan dialihkan ke status <span className="font-mono text-amber-300">PENDING_ROLLOVER</span> dan menunggu verifikasi Project Manager (PM) untuk dijadwalkan ke hari kerja berikutnya.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">
                  Alasan Kendala Lapangan (Wajib)
                </label>
                <textarea
                  value={rolloverReason}
                  onChange={(e) => setRolloverReason(e.target.value)}
                  placeholder="Contoh: Hujan lebat disertai petir di lokasi tower BTS, instalasi kabel FO dihentikan demi keselamatan K3..."
                  rows={3}
                  className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500 resize-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setRolloverSlot(null)}
                  disabled={submittingRollover}
                  className="text-slate-400 hover:text-white text-xs h-9"
                >
                  Batal
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={submittingRollover}
                  className="bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs h-9 shadow"
                >
                  {submittingRollover ? "Mengirim..." : "Kirimkan ke PM"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};
