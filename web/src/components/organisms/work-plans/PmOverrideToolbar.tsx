/**
 * web/src/components/organisms/work-plans/PmOverrideToolbar.tsx
 * Panel kontrol khusus Project Manager (PM) & Operational Manager (OM).
 * Memungkinkan intervensi langsung terhadap jadwal berjalan (ONGOING) tanpa terkunci status.
 */

import React, { useState } from "react";
import { useSession } from "@/stores/sessionStore";
import { Button } from "@/components/atoms/Button";
import {
  CalendarClock,
  Layers,
  LockOpen,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/apiClient";
import { useQueryClient } from "@tanstack/react-query";

interface PmOverrideToolbarProps {
  planId?: string;
  currentStatus?: string;
  onOpenRescheduleModal?: () => void;
  className?: string;
}

export const PmOverrideToolbar: React.FC<PmOverrideToolbarProps> = ({
  planId,
  currentStatus = "ONGOING",
  onOpenRescheduleModal,
  className = "",
}) => {
  const { me } = useSession();
  const qc = useQueryClient();
  const [updatingStatus, setUpdatingStatus] = useState<boolean>(false);

  // Periksa apakah pengguna memiliki hak PM/OM/Super Admin
  const isPmOrHigher =
    me?.role === "PROJECT_MANAGER" ||
    me?.role === "OPERATIONAL_MANAGER" ||
    me?.role === "SUPER_ADMIN" ||
    me?.role === "PM" ||
    me?.role === "ADMIN" ||
    !!me?.permissions.includes("create:plan");

  if (!isPmOrHigher) {
    return null;
  }

  const handleStatusChange = async (newStatus: string) => {
    if (!planId || newStatus === currentStatus) return;
    setUpdatingStatus(true);
    try {
      await api.patch(`/work-plans/${planId}`, { status: newStatus });
      toast.success(`Status rencana kerja berhasil diubah ke ${newStatus}!`);
      qc.invalidateQueries({ queryKey: ["work-plans"] });
      qc.invalidateQueries({ queryKey: ["work-plan", planId] });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal mengubah status rencana kerja.";
      toast.error(msg);
    } finally {
      setUpdatingStatus(false);
    }
  };

  return (
    <div
      className={`bg-gradient-to-r from-amber-950/60 via-slate-900 to-amber-950/40 border border-amber-600/40 rounded-xl p-3.5 shadow-lg flex flex-wrap items-center justify-between gap-3 text-slate-200 ${className}`}
    >
      <div className="flex items-center gap-2.5">
        <div className="p-2 bg-amber-500/20 text-amber-400 rounded-lg border border-amber-500/30 shrink-0">
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-white tracking-wide">
              PM Full Override Toolbar
            </h4>
            <span className="text-[10px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
              <LockOpen className="w-2.5 h-2.5" />
              Status Berjalan Tidak Terkunci
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Anda memiliki otoritas penuh untuk menggeser slot jadwal, mengubah status, dan mengatasi bentrok teknisi.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {/* Instant Status Switcher */}
        {planId && (
          <div className="flex items-center gap-1.5 bg-slate-900/90 border border-slate-700/80 rounded-lg px-2.5 py-1">
            <Layers className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-xs text-slate-400">Status:</span>
            <select
              value={currentStatus}
              disabled={updatingStatus}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="bg-transparent text-xs font-semibold text-amber-300 focus:outline-none cursor-pointer"
            >
              <option value="DRAFT" className="bg-slate-900 text-slate-200">DRAFT</option>
              <option value="SUBMITTED" className="bg-slate-900 text-slate-200">SUBMITTED</option>
              <option value="APPROVED" className="bg-slate-900 text-slate-200">APPROVED</option>
              <option value="ONGOING" className="bg-slate-900 text-emerald-300">ONGOING</option>
              <option value="COMPLETED" className="bg-slate-900 text-sky-300">COMPLETED</option>
            </select>
          </div>
        )}

        {/* Tombol Reschedule & Move Slot */}
        {onOpenRescheduleModal && (
          <Button
            size="sm"
            onClick={onOpenRescheduleModal}
            className="bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs h-8 gap-1.5 shadow"
          >
            <CalendarClock className="w-3.5 h-3.5" />
            Geser / Reschedule Tugas
          </Button>
        )}
      </div>
    </div>
  );
};
