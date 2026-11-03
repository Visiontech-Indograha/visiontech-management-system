import { formatDate } from "@/lib/format";
import { useSession } from "@/stores/sessionStore";
import { useState } from "react";
import {
  Building,
  Calendar,
  CheckCircle2,
  Clock,
  FileCheck2,
  Layers,
  MapPin,
  Package,
  PenTool,
  ShieldCheck,
  UserCheck,
} from "@/components/molecules/Glyphs";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import {
  TabsBlock,
  TabsBlockList,
  TabsBlockTrigger,
  TabsBlockContent,
} from "@/components/molecules/TabsBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { useWorkCompletion } from "@/services/workCompletionService";
import { PhotoStrip } from "@/components/organisms/PhotoStrip";
import { photoRefs } from "@/lib/photoRefs";
import { WorkCompletionBomTable } from "./WorkCompletionBomTable";
import { WorkCompletionExportPanel } from "./WorkCompletionExportPanel";
import { PmSignatureDialog } from "./PmSignatureDialog";

interface WorkCompletionDetailModalProps {
  completionId: string | null;
  onClose: () => void;
  canManage: boolean;
}

export function WorkCompletionDetailModal({
  completionId,
  onClose,
  canManage,
}: WorkCompletionDetailModalProps) {
  const [activeTab, setActiveTab] = useState<string>("ringkasan");
  // Tanda tangan BAST sebagai PM hanya untuk PM/OM divisi (API sign_order); OPS & admin tidak menandatangani.
  const role = useSession().me?.role ?? "";
  const canSignAsPm = ["PROJECT_MANAGER", "OPERATIONAL_MANAGER", "SUPER_ADMIN"].includes(role);
  const [isSignDialogOpen, setIsSignDialogOpen] = useState(false);

  const { data: order, isPending, isError } = useWorkCompletion(completionId || "");

  if (!completionId) return null;

  const completedUnits = order?.completed_target_unit ?? 0;
  const targetUnits = order?.total_target_unit ?? 1;
  const progressPct = Math.min(100, Math.round((completedUnits / Math.max(1, targetUnits)) * 100));

  return (
    <VmsDialog
      open={Boolean(completionId)}
      title={order?.project_title || "Detail pekerjaan klien"}
      onClose={onClose}
      size="xl"
    >
      <div className="space-y-4">
        {/* Header Metadata */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
          <div>
            <TextBlock as="span" className="text-xs font-bold uppercase tracking-wider text-primary">
              {order?.client_name || "Detail pekerjaan klien"}
            </TextBlock>
            {order?.order_number && (
              <TextBlock className="text-xs text-mist">
                No. surat perintah kerja: {order.order_number}
              </TextBlock>
            )}
          </div>

        </div>

        {isPending && (
          <div className="space-y-3 py-6">
            <LoadingBar className="h-12" />
            <LoadingBar className="h-32" />
          </div>
        )}

        {isError && (
          <div className="py-6 text-center">
            <TextBlock className="mb-2 text-sm text-danger">
              Gagal memuat detail order proyek.
            </TextBlock>
          </div>
        )}

        {order && (
          <div className="py-2">
            <TabsBlock value={activeTab} onValueChange={setActiveTab}>
              <TabsBlockList className="mb-4 w-full justify-start border-b border-line bg-transparent p-0">
                <TabsBlockTrigger
                  value="ringkasan"
                  className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                >
                  <Layers className="mr-1.5 h-4 w-4" />
                  <TextBlock as="span">Ringkasan & hasil kerja</TextBlock>
                </TabsBlockTrigger>
                <TabsBlockTrigger
                  value="bom"
                  className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                >
                  <Package className="mr-1.5 h-4 w-4" />
                  <TextBlock as="span">Daftar material</TextBlock>
                </TabsBlockTrigger>
                <TabsBlockTrigger
                  value="bast"
                  className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                >
                  <FileCheck2 className="mr-1.5 h-4 w-4" />
                  <TextBlock as="span">Tanda tangan serah terima</TextBlock>
                </TabsBlockTrigger>
              </TabsBlockList>

              {/* TAB 1: RINGKASAN */}
              <TabsBlockContent value="ringkasan" className="space-y-4">
                {/* Progress Bar & Deliverables Volume */}
                <div className="rounded-control bg-slate-50 p-4 dark:bg-slate-900/60 border border-line">
                  <div className="mb-2 flex items-center justify-between">
                    <div>
                      <TextBlock className="text-xs font-semibold text-mist uppercase tracking-wider">
                        Hasil utama yang sudah selesai
                      </TextBlock>
                      <TextBlock className="text-xl font-bold text-ink">
                        {completedUnits} / {targetUnits} {order.unit_measure}
                      </TextBlock>
                    </div>
                    <TextBlock className="text-lg font-bold text-primary">
                      {progressPct}%
                    </TextBlock>
                  </div>
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                    <div
                      className={`h-full transition-all duration-300 ${
                        progressPct >= 100 ? "bg-emerald-500" : "bg-primary"
                      }`}
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>
                  <TextBlock className="mt-2 text-2xs text-mist">
                    *Yang dihitung hanya pekerjaan utama (mis. kamera terpasang). Survei & persiapan dicatat sebagai pendukung.
                  </TextBlock>
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div className="rounded-control border border-line p-3 space-y-2">
                    <div className="flex items-center gap-2 text-xs text-mist">
                      <Calendar className="h-4 w-4 text-primary shrink-0" />
                      <TextBlock as="span">Tanggal dikerjakan:</TextBlock>
                    </div>
                    <TextBlock className="font-semibold text-ink pl-6">
                      {order.start_work_date
                        ? `${formatDate(order.start_work_date)} s.d. ${order.end_work_date ? formatDate(order.end_work_date) : "sekarang"}`
                        : "Belum terjadwal di rencana kerja harian"}
                    </TextBlock>
                  </div>

                  <div className="rounded-control border border-line p-3 space-y-2">
                    <div className="flex items-center gap-2 text-xs text-mist">
                      <Building className="h-4 w-4 text-primary shrink-0" />
                      <TextBlock as="span">Divisi & PM:</TextBlock>
                    </div>
                    <TextBlock className="font-semibold text-ink pl-6">
                      {order.division_name || "Divisi Operasional"} • {order.pm_name || "PM"}
                    </TextBlock>
                  </div>

                  <div className="rounded-control border border-line p-3 space-y-2 md:col-span-2">
                    <div className="flex items-center gap-2 text-xs text-mist">
                      <MapPin className="h-4 w-4 text-rose-500 shrink-0" />
                      <TextBlock as="span">Lokasi:</TextBlock>
                    </div>
                    <TextBlock className="font-medium text-ink pl-6">
                      {order.site_address || "Lokasi belum ditentukan secara spesifik"}
                    </TextBlock>
                    {order.site_lat != null && order.site_lng != null && (
                      <TextBlock className="text-xs text-mist pl-6">
                        Koordinat GPS: {order.site_lat}, {order.site_lng}
                      </TextBlock>
                    )}
                  </div>
                </div>

                {order.summary_notes && (
                  <div className="rounded-control border border-line p-3 bg-hover/20">
                    <TextBlock className="text-xs font-semibold text-mist uppercase tracking-wider mb-1">
                      Ringkasan pekerjaan
                    </TextBlock>
                    <TextBlock className="text-sm text-ink whitespace-pre-wrap">
                      {order.summary_notes}
                    </TextBlock>
                  </div>
                )}

                {photoRefs(order.realization_photos_json).length > 0 && (
                  <div className="rounded-control border border-line p-3 bg-hover/20">
                    <TextBlock className="text-xs font-semibold text-mist uppercase tracking-wider mb-2">
                      Foto hasil pekerjaan
                    </TextBlock>
                    <PhotoStrip photos={photoRefs(order.realization_photos_json)} alt="Foto hasil pekerjaan" />
                  </div>
                )}
              </TabsBlockContent>

              {/* TAB 2: BILL OF MATERIALS */}
              <TabsBlockContent value="bom" className="pt-2">
                <WorkCompletionBomTable
                  completionId={order.completion_id}
                  canManage={canManage}
                />
              </TabsBlockContent>

              {/* TAB 3: PENGESAHAN & BAST */}
              <TabsBlockContent value="bast" className="space-y-4 pt-2">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Status Pengesahan Lapangan */}
                  <div className="rounded-control border border-line p-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <UserCheck className="h-5 w-5 text-primary" />
                      <TextBlock className="font-semibold text-ink">
                        Pengesahan Team Leader
                      </TextBlock>
                    </div>
                    {order.leader_signed_at ? (
                      <div className="rounded bg-emerald-500/10 p-2.5 text-xs text-emerald-700 dark:text-emerald-300">
                        <div className="flex items-center gap-1.5 font-bold mb-0.5">
                          <CheckCircle2 className="h-4 w-4" />
                          <TextBlock as="span">Sudah Ditandatangani</TextBlock>
                        </div>
                        <TextBlock>
                          Waktu: {new Date(order.leader_signed_at).toLocaleString("id-ID")}
                        </TextBlock>
                      </div>
                    ) : (
                      <div className="rounded bg-amber-500/10 p-2.5 text-xs text-amber-700 dark:text-amber-300">
                        <div className="flex items-center gap-1.5 font-semibold mb-0.5">
                          <Clock className="h-4 w-4" />
                          <TextBlock as="span">Menunggu Pengesahan Lapangan</TextBlock>
                        </div>
                        <TextBlock>
                          Team leader menandatangani laporan setelah seluruh pekerjaan tuntas.
                        </TextBlock>
                      </div>
                    )}
                  </div>

                  {/* Status Validasi PM */}
                  <div className="rounded-control border border-line p-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="h-5 w-5 text-primary" />
                      <TextBlock className="font-semibold text-ink">
                        Validasi Project Manager
                      </TextBlock>
                    </div>
                    {order.pm_signed_at ? (
                      <div className="rounded bg-emerald-500/10 p-2.5 text-xs text-emerald-700 dark:text-emerald-300">
                        <div className="flex items-center gap-1.5 font-bold mb-0.5">
                          <CheckCircle2 className="h-4 w-4" />
                          <TextBlock as="span">Divalidasi oleh PM</TextBlock>
                        </div>
                        <TextBlock>
                          Penandatangan: {order.pm_signer_name || "Project Manager"}
                        </TextBlock>
                        <TextBlock>
                          Waktu: {new Date(order.pm_signed_at).toLocaleString("id-ID")}
                        </TextBlock>
                      </div>
                    ) : (
                      <div className="space-y-2.5">
                        <div className="rounded bg-amber-500/10 p-2.5 text-xs text-amber-700 dark:text-amber-300">
                          <div className="flex items-center gap-1.5 font-semibold mb-0.5">
                            <Clock className="h-4 w-4" />
                            <TextBlock as="span">
                              {order.leader_signed_at
                                ? "Menunggu Tanda Tangan PM"
                                : "Menunggu Pengesahan Lapangan Lebih Dulu"}
                            </TextBlock>
                          </div>
                          <TextBlock>
                            {order.leader_signed_at
                              ? "Ketua tim telah mengesahkan laporan. PM dapat memeriksa hasil kerja dan menandatangani BAST."
                              : "Ketua tim harus menandatangani berita acara lebih dulu sebelum PM dapat memvalidasi."}
                          </TextBlock>
                        </div>
                        {order.leader_signed_at && canSignAsPm && (
                          <ActionButton
                            type="button"
                            variant="default"
                            size="sm"
                            className="w-full"
                            onClick={() => setIsSignDialogOpen(true)}
                          >
                            <PenTool className="mr-1.5 h-4 w-4" />
                            <TextBlock as="span">Tandatangani BAST (Project Manager)</TextBlock>
                          </ActionButton>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Digital Signature Hash Card */}
                <div className="rounded-control border border-line p-4 bg-slate-50 dark:bg-slate-900/60">
                  <div className="mb-1 flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-600" />
                    <TextBlock className="text-xs font-semibold text-ink uppercase tracking-wider">
                      Digital Signature Integrity Hash (SHA-256)
                    </TextBlock>
                  </div>
                  <TextBlock className="font-mono text-xs text-mist break-all bg-surface p-2 rounded border border-line">
                    {order.signature_hash || "Belum ditandatangani."}
                  </TextBlock>
                  <TextBlock className="mt-1 text-2xs text-mist">
                    Kode ini membuktikan dokumen serah terima asli dan tidak diubah setelah ditandatangani.
                  </TextBlock>
                </div>

                <WorkCompletionExportPanel completionId={order.completion_id} signed={!!order.signature_hash} />
              </TabsBlockContent>
            </TabsBlock>
          </div>
        )}
        {order && (
          <PmSignatureDialog
            open={isSignDialogOpen}
            completionId={order.completion_id}
            projectTitle={order.project_title}
            onClose={() => setIsSignDialogOpen(false)}
          />
        )}
      </div>
    </VmsDialog>
  );
}
