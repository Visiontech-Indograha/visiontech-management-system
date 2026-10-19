/**
 * web/src/components/organisms/work-plans/TaskChainCompletionDialog.tsx
 * Dialog interaktif untuk memvisualisasikan silsilah rantai tugas rollover (Task Chain),
 * memantau akumulasi capaian volume lintas hari dan lintas minggu,
 * serta menerbitkan Berita Acara (Work Completion) secara otomatis saat capaian mencapai 100%.
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
  AlertCircle,
  CheckCircle2,
  Clock,
  FileCheck2,
  FileText,
  Layers,
  Loader2,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import {
  useTaskChainStatus,
  useGenerateWorkCompletion,
} from "@/services/workPlanV2Service";
import type { TaskChainItemDetail } from "@/services/planItemService";

interface TaskChainCompletionDialogProps {
  itemId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const TaskChainCompletionDialog: React.FC<TaskChainCompletionDialogProps> = ({
  itemId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { data: chain, isLoading, error, refetch } = useTaskChainStatus(isOpen ? itemId : null);
  const generateCompletionMut = useGenerateWorkCompletion();

  const [clientName, setClientName] = useState<string>("");
  const [projectTitle, setProjectTitle] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!itemId) return;

    setIsGenerating(true);
    try {
      const res = await generateCompletionMut.mutateAsync({
        itemId,
        payload: {
          client_name: clientName.trim() || undefined,
          project_title: projectTitle.trim() || undefined,
        },
      });
      toast.success(res.message || "Berita Acara Work Completion berhasil diterbitkan!");
      refetch();
      onSuccess?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal menerbitkan Berita Acara.";
      toast.error(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "DONE":
      case "COMPLETED":
        return "bg-emerald-950/80 text-emerald-400 border-emerald-800";
      case "SHIFTED_DAY":
        return "bg-amber-950/80 text-amber-300 border-amber-800";
      case "ALLOCATED_NEXT_WEEK":
        return "bg-sky-950/80 text-sky-300 border-sky-800";
      case "IN_PROGRESS":
        return "bg-indigo-950/80 text-indigo-300 border-indigo-800";
      case "PENDING_ROLLOVER":
        return "bg-orange-950/80 text-orange-300 border-orange-800 animate-pulse";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto p-6 bg-slate-900 border-slate-800 text-white shadow-2xl rounded-2xl">
        <DialogHeader className="space-y-1.5 pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-sky-400" />
            <DialogTitle className="text-lg font-semibold text-white">
              Silsilah Rantai Tugas & Akumulasi Capaian
            </DialogTitle>
          </div>
          <p className="text-xs text-slate-400">
            Pelacakan riwayat rollover (Kasus 6A: Geser Hari & 6B: Lintas Minggu) menuju penerbitan Berita Acara (Work Completion).
          </p>
        </DialogHeader>

        {isLoading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-3 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
            <p className="text-xs font-medium">Memuat silsilah rantai tugas...</p>
          </div>
        ) : error || !chain ? (
          <div className="py-8 text-center text-slate-400 space-y-2">
            <AlertCircle className="w-8 h-8 text-rose-500 mx-auto" />
            <p className="text-sm font-medium text-rose-400">Gagal memuat rantai tugas.</p>
            <p className="text-xs text-slate-500">Tugas mungkin tidak memiliki keterkaitan rollover atau telah dihapus.</p>
          </div>
        ) : (
          <div className="space-y-5 pt-3">
            {/* Ringkasan Akumulasi Volume */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 bg-slate-950/80 border border-slate-800 rounded-xl">
              <div className="space-y-1">
                <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                  Target Pokok Awal
                </span>
                <p className="text-xl font-bold text-white">
                  {chain.initial_total_target}{" "}
                  <span className="text-xs font-normal text-slate-400">Unit</span>
                </p>
                <p className="text-[11px] text-slate-500">Dari butir tugas pertama</p>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                  Akumulasi Selesai
                </span>
                <p className="text-xl font-bold text-sky-400">
                  {chain.total_completed_across_weeks}{" "}
                  <span className="text-xs font-normal text-slate-400">/ {chain.initial_total_target} Unit</span>
                </p>
                <p className="text-[11px] text-slate-500">Tercapai di semua tahapan</p>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                  Progres Rantai
                </span>
                <div className="flex items-center gap-2">
                  <p className="text-xl font-bold text-emerald-400">
                    {chain.total_progress_percent}%
                  </p>
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden mt-1">
                  <div
                    className={`h-full transition-all duration-500 ${
                      chain.total_progress_percent >= 100 ? "bg-emerald-500" : "bg-sky-500"
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, chain.total_progress_percent))}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Status Kelayakan Berita Acara */}
            <div
              className={`p-3 rounded-xl border flex items-center justify-between gap-3 text-xs ${
                chain.is_eligible_for_completion
                  ? "bg-emerald-950/40 border-emerald-800/80 text-emerald-200"
                  : "bg-amber-950/40 border-amber-800/80 text-amber-200"
              }`}
            >
              <div className="flex items-center gap-2.5">
                {chain.is_eligible_for_completion ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                ) : (
                  <Clock className="w-5 h-5 text-amber-400 shrink-0" />
                )}
                <div>
                  <p className="font-semibold">{chain.status_label}</p>
                  <p className="text-[11px] opacity-80">
                    {chain.is_eligible_for_completion
                      ? "Seluruh volume tugas telah rampung 100%. Siap diterbitkan menjadi Work Completion."
                      : "Pekerjaan belum tuntas sepenuhnya. Berita Acara dapat dibuat setelah sisa unit diselesaikan."}
                  </p>
                </div>
              </div>

              {chain.existing_completion_id && (
                <span className="px-2.5 py-1 rounded-md bg-emerald-900/60 border border-emerald-700/60 text-emerald-300 font-mono text-[11px] shrink-0 flex items-center gap-1">
                  <FileCheck2 className="w-3.5 h-3.5" />
                  ID Terbit
                </span>
              )}
            </div>

            {/* Visualisasi Timeline Rantai Tugas */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-sky-400" />
                Tahapan Rantai Tugas ({chain.items?.length || 0} Mata Rantai)
              </h4>

              <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-800">
                {chain.items?.map((it: TaskChainItemDetail, idx: number) => {
                  const isCurrent = it.item_id === itemId;
                  return (
                    <div key={it.item_id} className="relative flex items-start gap-3 pl-1">
                      {/* Node Bullet */}
                      <div
                        className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-[11px] font-bold border z-10 ${
                          it.status === "DONE"
                            ? "bg-emerald-900 border-emerald-600 text-emerald-300"
                            : isCurrent
                            ? "bg-sky-900 border-sky-500 text-sky-200"
                            : "bg-slate-800 border-slate-700 text-slate-400"
                        }`}
                      >
                        {idx + 1}
                      </div>

                      {/* Card Item */}
                      <div
                        className={`flex-1 p-3 rounded-xl border text-xs space-y-1.5 transition-all ${
                          isCurrent
                            ? "bg-slate-800/80 border-sky-600/70 shadow-md ring-1 ring-sky-500/30"
                            : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                        }`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white">{it.title}</span>
                            {isCurrent && (
                              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800">
                                Posisi Saat Ini
                              </span>
                            )}
                          </div>
                          <span
                            className={`text-[10px] font-medium px-2 py-0.5 rounded border ${getStatusBadge(
                              it.status
                            )}`}
                          >
                            {it.status}
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-slate-400 text-[11px]">
                          <span>
                            Tanggal:{" "}
                            <strong className="text-slate-200">
                              {it.work_date || "Sesuai Jadwal"}
                            </strong>
                          </span>
                          <span>
                            Target Sisa/Tahap:{" "}
                            <strong className="text-slate-200">{it.target_qty} unit</strong>
                          </span>
                          <span>
                            Selesai di Tahap ini:{" "}
                            <strong className="text-emerald-400">{it.completed_qty} unit</strong>
                          </span>
                          <span>
                            Progres:{" "}
                            <strong className="text-white">{it.progress_percent}%</strong>
                          </span>
                        </div>

                        {it.completion_id && (
                          <div className="text-[11px] text-emerald-400 flex items-center gap-1 font-mono pt-0.5">
                            <FileCheck2 className="w-3 h-3" />
                            <span>Tertaut Berita Acara: {it.completion_id}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Form & Tombol Generate Berita Acara (Work Completion) */}
            {chain.is_eligible_for_completion && !chain.existing_completion_id && (
              <form onSubmit={handleGenerate} className="p-4 bg-emerald-950/30 border border-emerald-800/80 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-emerald-400">
                  <Sparkles className="w-4 h-4" />
                  <h4 className="text-xs font-semibold uppercase tracking-wider">
                    Terbitkan Berita Acara (Work Completion) Otomatis
                  </h4>
                </div>
                <p className="text-xs text-slate-300">
                  Sistem akan mengompilasi total volume <strong>{chain.initial_total_target} unit</strong> dari seluruh tahapan rantai ke dalam dokumen Berita Acara resmi PT Visiontech Indograha.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <div className="space-y-1">
                    <label className="text-[11px] font-medium text-slate-300">Nama Klien / Perusahaan</label>
                    <input
                      type="text"
                      value={clientName}
                      onChange={(e) => setClientName(e.target.value)}
                      placeholder="Contoh: PT Pertamina EP"
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[11px] font-medium text-slate-300">Judul Proyek / SPK</label>
                    <input
                      type="text"
                      value={projectTitle}
                      onChange={(e) => setProjectTitle(e.target.value)}
                      placeholder="Contoh: Pengadaan & Pemasangan Titik Akses..."
                      className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end pt-2">
                  <Button
                    type="submit"
                    disabled={isGenerating}
                    size="sm"
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs h-9 px-4 gap-1.5 shadow-lg shadow-emerald-950"
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Mengompilasi Berita Acara...
                      </>
                    ) : (
                      <>
                        <FileCheck2 className="w-3.5 h-3.5" />
                        Terbitkan Work Completion
                      </>
                    )}
                  </Button>
                </div>
              </form>
            )}

            {/* Sudah Ada Berita Acara */}
            {chain.existing_completion_id && (
              <div className="p-3 bg-slate-950 border border-emerald-800/80 rounded-xl flex items-center justify-between text-xs text-emerald-300">
                <div className="flex items-center gap-2">
                  <FileCheck2 className="w-4 h-4 text-emerald-400" />
                  <span>
                    Berita Acara telah aktif dengan Completion ID:{" "}
                    <strong className="font-mono text-white">{chain.existing_completion_id}</strong>
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end pt-3 border-t border-slate-800">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-slate-400 hover:text-white text-xs h-8"
          >
            Tutup
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
