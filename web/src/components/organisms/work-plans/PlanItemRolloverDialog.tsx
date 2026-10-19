/**
 * web/src/components/organisms/work-plans/PlanItemRolloverDialog.tsx
 * Dialog interaktif untuk mengeksekusi Rollover Tugas (Kasus 6A: Geser Hari & Kasus 6B: Alokasikan ke Minggu Depan).
 * Memindahkan sisa volume target ke hari kerja tujuan secara otomatis.
 */

import React, { useState } from "react";
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
  ArrowRight,
  Calendar,
  Send,
} from "lucide-react";
import { pmApproveOrMoveItem, type ItemScheduleSlot } from "@/services/planItemService";

interface PlanItemRolloverDialogProps {
  isOpen: boolean;
  onClose: () => void;
  item: ItemScheduleSlot | null;
  dailyPlanId: string;
  currentDate: string;
  availableDays?: Array<{ daily_plan_id: string; work_date: string; site_name?: string }>;
  onSuccess?: () => void;
}

export const PlanItemRolloverDialog: React.FC<PlanItemRolloverDialogProps> = ({
  isOpen,
  onClose,
  item,
  dailyPlanId,
  currentDate,
  availableDays = [],
  onSuccess,
}) => {
  const [targetDailyId, setTargetDailyId] = useState<string>("");
  const [reason, setReason] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Filter hari yang bukan hari saat ini
  const otherDays = availableDays.filter((d) => d.daily_plan_id !== dailyPlanId);

  // Set default target day saat dialog dibuka
  React.useEffect(() => {
    if (otherDays.length > 0 && !targetDailyId) {
      setTargetDailyId(otherDays[0].daily_plan_id);
    }
    setReason("");
  }, [isOpen, otherDays, targetDailyId]);

  if (!isOpen || !item) return null;

  const targetQty = Number(item.target_qty || 0);
  const completedQty = Number(item.completed_qty || 0);
  const remQty = Math.max(0, targetQty - completedQty);

  const selectedTargetDay = availableDays.find((d) => d.daily_plan_id === targetDailyId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetDailyId) {
      toast.error("Pilih hari kerja tujuan untuk pemindahan tugas.");
      return;
    }
    if (!reason.trim()) {
      toast.error("Alasan kendala lapangan / persetujuan PM wajib diisi.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await pmApproveOrMoveItem(item.item_id, {
        action: "MOVE_SLOT",
        pm_override_reason: reason.trim(),
        target_daily_plan_id: targetDailyId,
      });

      toast.success(res.message || "Tugas berhasil di-rollover!");
      onClose();
      onSuccess?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal memproses rollover tugas.";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg p-6 bg-slate-900 border-slate-800 text-white shadow-2xl rounded-2xl">
        <DialogHeader className="space-y-1.5 pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Send className="w-5 h-5 text-amber-400" />
            <DialogTitle className="text-base font-semibold text-white">
              Rollover Tugas ke Jadwal Berikutnya
            </DialogTitle>
          </div>
          <p className="text-xs text-slate-400">
            Pindahkan sisa target pekerjaan yang belum rampung hari ini ({currentDate}) ke slot hari kerja tujuan.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-3">
          {/* Rincian Tugas Saat Ini */}
          <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-white text-sm">{item.title}</span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {item.status}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 pt-1 text-center">
              <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Target Awal</span>
                <p className="text-sm font-bold text-white">{targetQty} Unit</p>
              </div>
              <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Selesai</span>
                <p className="text-sm font-bold text-emerald-400">{completedQty} Unit</p>
              </div>
              <div className="p-2 rounded-lg bg-amber-950/40 border border-amber-800/60">
                <span className="text-[10px] text-amber-300 uppercase font-medium">Sisa Rollover</span>
                <p className="text-sm font-bold text-amber-300">{remQty > 0 ? remQty : targetQty} Unit</p>
              </div>
            </div>
          </div>

          {/* Pilih Hari Tujuan */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-sky-400" />
              Pilih Hari Kerja Tujuan (Target Day)
            </label>

            {otherDays.length > 0 ? (
              <select
                value={targetDailyId}
                onChange={(e) => setTargetDailyId(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
                required
              >
                {otherDays.map((day) => (
                  <option key={day.daily_plan_id} value={day.daily_plan_id}>
                    {day.work_date} {day.site_name ? `• ${day.site_name}` : ""}
                  </option>
                ))}
              </select>
            ) : (
              <div className="p-3 bg-amber-950/30 border border-amber-800/60 rounded-lg text-xs text-amber-200">
                Tidak ada hari kerja lain di minggu yang sama. Tugas dapat dialokasikan ke jadwal mingguan berikutnya.
              </div>
            )}

            {selectedTargetDay && (
              <p className="text-[11px] text-slate-400 flex items-center gap-1 pt-0.5">
                <ArrowRight className="w-3 h-3 text-emerald-400" />
                Tugas lanjutan otomatis dibuat di tanggal:{" "}
                <strong className="text-slate-200">{selectedTargetDay.work_date}</strong>
              </p>
            )}
          </div>

          {/* Input Alasan Rollover */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              Alasan Kendala Lapangan / Catatan PM (Wajib)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Contoh: Kondisi cuaca hujan deras di site BTS Dumai, pekerjaan dilanjutkan esok hari..."
              rows={3}
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500 resize-none"
              required
            />
          </div>

          {/* Tombol Aksi */}
          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-slate-400 hover:text-white text-xs h-9"
            >
              Batal
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting || otherDays.length === 0}
              className="bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs h-9 px-4 gap-1.5 shadow"
            >
              <Send className="w-3.5 h-3.5" />
              {isSubmitting ? "Memproses Rollover..." : "Konfirmasi & Geser Tugas"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
