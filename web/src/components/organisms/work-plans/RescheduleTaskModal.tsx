/**
 * web/src/components/organisms/work-plans/RescheduleTaskModal.tsx
 * Modal interaktif untuk memindahkan tugas ke slot waktu atau tanggal lain (PM Full Override).
 * Dilengkapi dengan detektor tabrakan jadwal teknisi & armada secara langsung.
 */

import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/atoms/Dialog";
import { Button } from "@/components/atoms/Button";
import { toast } from "sonner";
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Clock,
  ShieldAlert,
} from "lucide-react";
import {
  checkScheduleConflict,
  pmApproveOrMoveItem,
  type CheckConflictOut,
  type ItemScheduleSlot,
} from "@/services/planItemService";

interface RescheduleTaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: ItemScheduleSlot | null;
  currentDate: string;
  availableDays?: Array<{ daily_plan_id: string; work_date: string; site_name?: string }>;
  onSuccess?: () => void;
}

export const RescheduleTaskModal: React.FC<RescheduleTaskModalProps> = ({
  isOpen,
  onClose,
  item,
  currentDate,
  availableDays = [],
  onSuccess,
}) => {
  const [targetDailyId, setTargetDailyId] = useState<string>("");
  const [startTime, setStartTime] = useState<string>("08:00");
  const [endTime, setEndTime] = useState<string>("12:00");
  const [overrideReason, setOverrideReason] = useState<string>("");
  const [checkingConflict, setCheckingConflict] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [conflictResult, setConflictResult] = useState<CheckConflictOut | null>(null);

  useEffect(() => {
    if (item) {
      setStartTime(item.start_time?.slice(0, 5) || "08:00");
      setEndTime(item.end_time?.slice(0, 5) || "12:00");
      setOverrideReason("");
      setConflictResult(null);
      if (availableDays.length > 0) {
        setTargetDailyId(availableDays[0].daily_plan_id);
      }
    }
  }, [item, availableDays]);

  if (!isOpen || !item) return null;

  const selectedDay = availableDays.find((d) => d.daily_plan_id === targetDailyId);
  const targetDate = selectedDay?.work_date || currentDate;

  const handleCheckConflict = async () => {
    if (!startTime || !endTime) return;
    setCheckingConflict(true);
    try {
      const result = await checkScheduleConflict({
        work_date: targetDate,
        start_time: `${startTime}:00`,
        end_time: `${endTime}:00`,
        employee_ids: item.assigned_employee_ids || [],
        exclude_item_id: item.item_id,
      });
      setConflictResult(result);
      if (result.has_conflict) {
        toast.warning("Ditemukan potensi tabrakan jadwal teknisi/armada!");
      } else {
        toast.success("Tidak ada bentrok jadwal pada slot waktu ini.");
      }
    } catch {
      toast.error("Gagal memeriksa tabrakan jadwal.");
    } finally {
      setCheckingConflict(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideReason.trim()) {
      toast.error("Alasan pemindahan tugas (PM Override) wajib diisi.");
      return;
    }

    setSubmitting(true);
    try {
      await pmApproveOrMoveItem(item.item_id, {
        action: "MOVE_SLOT",
        pm_override_reason: overrideReason.trim(),
        target_daily_plan_id: targetDailyId || undefined,
        target_start_time: `${startTime}:00`,
        target_end_time: `${endTime}:00`,
      });

      toast.success("Tugas berhasil dipindahkan ke slot baru!");
      onSuccess?.();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal memindahkan tugas.";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg p-6 bg-slate-900 border-slate-800 text-white shadow-2xl rounded-xl">
        <DialogHeader className="space-y-1">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-amber-400" />
            <DialogTitle className="text-base font-semibold text-white">
              Reschedule & Move Slot (PM Override)
            </DialogTitle>
          </div>
          <p className="text-xs text-slate-400">
            Pindahkan tugas <span className="text-slate-200 font-medium">"{item.title}"</span> ke tanggal atau jam lain.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {/* Pemilihan Hari Tujuan */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-sky-400" />
              Pilih Hari / Tanggal Target
            </label>
            <select
              value={targetDailyId}
              onChange={(e) => setTargetDailyId(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              {availableDays.map((d) => (
                <option key={d.daily_plan_id} value={d.daily_plan_id}>
                  {d.work_date} — {d.site_name || "Site"}
                </option>
              ))}
            </select>
          </div>

          {/* Slot Waktu Kerja */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Jam Mulai</label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Jam Selesai</label>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
                required
              />
            </div>
          </div>

          {/* Tombol Cek Bentrok Jadwal */}
          <div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCheckConflict}
              disabled={checkingConflict}
              className="w-full bg-slate-800/80 hover:bg-slate-700 text-sky-400 border-slate-700 text-xs h-8 gap-1.5"
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              {checkingConflict ? "Memeriksa..." : "Periksa Potensi Bentrok Jadwal"}
            </Button>
          </div>

          {/* Peringatan Bentrok Jadwal */}
          {conflictResult && (
            <div
              className={`p-3 rounded-lg border text-xs space-y-1.5 ${
                conflictResult.has_conflict
                  ? "bg-amber-950/40 border-amber-800/60 text-amber-200"
                  : "bg-emerald-950/40 border-emerald-800/60 text-emerald-200"
              }`}
            >
              <div className="flex items-center gap-1.5 font-medium">
                {conflictResult.has_conflict ? (
                  <>
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    <span>Terdeteksi {conflictResult.conflicts.length} Tabrakan Jadwal!</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Aman: Seluruh teknisi & armada bebas dari jadwal lain.</span>
                  </>
                )}
              </div>
              {conflictResult.has_conflict && (
                <ul className="list-disc list-inside space-y-0.5 text-slate-300 pl-1 text-[11px]">
                  {conflictResult.conflicts.map((c, idx) => (
                    <li key={idx}>
                      <span className="font-semibold text-amber-300">{c.entity_name}</span> bertugas di "{c.conflicting_title}" ({c.start_time?.slice(0, 5)} - {c.end_time?.slice(0, 5)})
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Alasan PM Override */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">
              Alasan Pemindahan / Override (Wajib)
            </label>
            <textarea
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="Contoh: Klien meminta reschedule karena izin akses site baru keluar hari berikutnya..."
              rows={2}
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500 resize-none"
              required
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onClose}
              disabled={submitting}
              className="text-slate-400 hover:text-white text-xs h-9"
            >
              Batal
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={submitting}
              className="bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs h-9 gap-1.5 shadow-md"
            >
              <Clock className="w-3.5 h-3.5" />
              {submitting ? "Memproses..." : "Terapkan Reschedule"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
