import L from "leaflet";
import { statusLabel } from "@/lib/labels";
import { errorMessage } from "@/lib/errors";
import { SurveyApproveButton } from "./SurveyApproveButton";
import { BastDownloadButtons } from "./BastDownloadButtons";
import { useEffect, useMemo, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import { toast } from "sonner";
import { useFileUrl } from "@/hooks/useFileUrl";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import {
  MapPin,
  Camera,
  Layers,
  Package,
  FileCheck2,
  X,
  Download,
  Map as MapIcon,
  List as ListIcon,
} from "@/components/molecules/Glyphs";
import {
  useWorkOrderDetail,
  useApplySurvey,
  downloadWorkOrderExport,
} from "@/services/workOrderService";
import "leaflet/dist/leaflet.css";

const SAT_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
/** Tombol tutup bawaan Leaflet berlabel "Close popup" (tanpa opsi bahasa); labelnya diganti saat popup dibuka. */
function indonesianCloseButton(e: L.PopupEvent) {
  const button = e.popup.getElement()?.querySelector(".leaflet-popup-close-button");
  button?.setAttribute("aria-label", "Tutup keterangan titik");
  button?.setAttribute("title", "Tutup keterangan titik");
}

const SAT_ATTR = "Imagery &copy; Esri, Maxar, Earthstar Geographics";

const createSurveyPin = (n: number) =>
  L.divIcon({
    className: "",
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
    html: `<div style="width:32px;height:32px;border-radius:50%;background:#0284C7;border:3px solid #ffffff;color:#ffffff;font:700 13px/26px sans-serif;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,0.45);cursor:pointer;transition:transform 0.15s ease;" onmouseover="this.style.transform='scale(1.15)'" onmouseout="this.style.transform='scale(1)'">${n}</div>`,
  });

function FitSurveyMap({ coords }: { coords: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    const trigger = () => {
      map.invalidateSize();
      if (coords.length === 1) {
        map.setView(coords[0], 18);
      } else if (coords.length > 1) {
        map.fitBounds(L.latLngBounds(coords), { padding: [60, 60], maxZoom: 18 });
      }
    };

    const t1 = setTimeout(trigger, 100);
    const t2 = setTimeout(trigger, 350);
    const t3 = setTimeout(trigger, 700);

    const container = map.getContainer();
    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined" && container) {
      ro = new ResizeObserver(() => map.invalidateSize());
      ro.observe(container);
    }

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      ro?.disconnect();
    };
  }, [map, coords]);

  return null;
}

interface WorkOrderSurveyReviewModalProps {
  workOrderId: string | null;
  onClose: () => void;
}

type PointPhotoRef = string | Record<string, unknown> | undefined;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Foto titik bisa berupa URL penuh, id berkas, atau objek {file_id | url | file_url}; id diubah jadi URL bertiket. */
function usePointPhotoUrl(p: PointPhotoRef): string {
  const raw =
    typeof p === "string"
      ? p
      : ((p?.url as string) || (p?.file_url as string) || (p?.file_id as string) || (p?.id as string) || "");
  const fileId = raw && UUID_RE.test(raw) ? raw : undefined;
  const { data } = useFileUrl(fileId, "view");
  return fileId ? (data ?? "") : raw;
}

/** Pratinjau foto titik di popup peta: klik untuk perbesar. */
function PointPhotoThumb({ photo, onOpen }: { photo: PointPhotoRef; onOpen: (url: string) => void }) {
  const url = usePointPhotoUrl(photo);
  if (!url) return null;
  return (
    <div
      onClick={() => onOpen(url)}
      className="cursor-pointer overflow-hidden rounded border border-border mt-1 h-28 bg-cover bg-center"
      style={{ backgroundImage: `url(${url})` }}
    />
  );
}

/** Kotak foto di galeri titik. */
function PointPhotoTile({ photo, onOpen }: { photo: PointPhotoRef; onOpen: (url: string) => void }) {
  const url = usePointPhotoUrl(photo);
  return (
    <ActionButton
      type="button"
      variant="ghost"
      size="sm"
      onClick={() => url && onOpen(url)}
      className="h-20 w-20 p-0 rounded-lg border border-border overflow-hidden bg-muted relative group shadow-xs hover:border-primary/50"
    >
      {url ? (
        <div
          className="h-full w-full bg-cover bg-center group-hover:scale-108 transition-transform duration-200"
          style={{ backgroundImage: `url(${url})` }}
        />
      ) : (
        <Camera className="h-6 w-6 text-muted-foreground m-auto" />
      )}
    </ActionButton>
  );
}

export function WorkOrderSurveyReviewModal({
  workOrderId,
  onClose,
}: WorkOrderSurveyReviewModalProps) {
  const { data: detail, isLoading } = useWorkOrderDetail(workOrderId || undefined);
  const applyMutation = useApplySurvey(workOrderId || "");
  const [selectedPhoto, setSelectedPhoto] = useState<string | null>(null);
  const [tileFailed, setTileFailed] = useState(false);
  const [activeTab, setActiveTab] = useState<"both" | "map" | "list">("both");

  const surveyPoints = detail?.survey_points;
  const validCoords = useMemo(() => {
    if (!surveyPoints) return [];
    return surveyPoints
      .filter((p) => p.site_lat != null && p.site_lng != null)
      .map((p) => [Number(p.site_lat), Number(p.site_lng)] as [number, number]);
  }, [surveyPoints]);

  if (!workOrderId) return null;

  const handleApply = async () => {
    try {
      await applyMutation.mutateAsync();
      toast.success("Hasil survei berhasil disetujui! Work order kini siap dijadwalkan.");
      onClose();
    } catch (err) {
      toast.error(errorMessage(err, "Hasil survei belum bisa disetujui. Coba lagi."));
    }
  };

  const isPendingApproval = detail?.status === "SURVEY_SUBMITTED";

  return (
    <VmsDialog
      open={Boolean(workOrderId)}
      onClose={onClose}
      title={`Rincian Tugas dan Dokumen Resmi — ${detail?.wo_number || "..."}`}
      size="2xl"
    >
      {isLoading || !detail ? (
        <div className="py-16 text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent align-[-0.125em]" />
          <TextBlock className="mt-3 text-muted-foreground">Memuat data hasil survei dan titik lokasi...</TextBlock>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Top Info Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-surface-elevated rounded-xl border border-border shadow-xs">
            <div className="min-w-0">
              <TextBlock className="font-bold text-lg text-ink truncate">{detail.title}</TextBlock>
              <div className="text-xs text-muted-foreground mt-0.5 flex flex-wrap items-center gap-1.5">
                <TextBlock as="span">Klien: </TextBlock>
                <TextBlock as="span" className="font-semibold text-ink">{detail.client_name}</TextBlock>
                <TextBlock as="span"> | Lokasi: </TextBlock>
                <TextBlock as="span" className="font-semibold text-ink">{detail.site_name || "Belum ada site"}</TextBlock>
                <TextBlock as="span"> ({detail.site_address || "-"})</TextBlock>
                <TextBlock as="span"> | Tim: </TextBlock>
                <TextBlock as="span" className="font-semibold text-ink">{detail.team_name || "Belum ditunjuk"}</TextBlock>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Tampilan Toggle View */}
              <div className="hidden sm:flex items-center bg-card rounded-lg border border-border p-1 gap-1">
                <ActionButton
                  type="button"
                  variant={activeTab === "both" ? "default" : "ghost"}
                  size="xs"
                  onClick={() => setActiveTab("both")}
                  className="h-7 px-2.5 text-xs gap-1"
                >
                  <Layers className="h-3.5 w-3.5" />
                  <TextBlock as="span">Peta dan Daftar</TextBlock>
                </ActionButton>
                <ActionButton
                  type="button"
                  variant={activeTab === "map" ? "default" : "ghost"}
                  size="xs"
                  onClick={() => setActiveTab("map")}
                  className="h-7 px-2.5 text-xs gap-1"
                >
                  <MapIcon className="h-3.5 w-3.5" />
                  <TextBlock as="span">Peta Saja</TextBlock>
                </ActionButton>
                <ActionButton
                  type="button"
                  variant={activeTab === "list" ? "default" : "ghost"}
                  size="xs"
                  onClick={() => setActiveTab("list")}
                  className="h-7 px-2.5 text-xs gap-1"
                >
                  <ListIcon className="h-3.5 w-3.5" />
                  <TextBlock as="span">Daftar Titik</TextBlock>
                </ActionButton>
              </div>

              <div
                className={`px-3 py-1 text-xs font-bold rounded-full ${
                  isPendingApproval
                    ? "bg-amber-500/10 text-amber-500 border border-amber-500/30 animate-pulse"
                    : "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30"
                }`}
              >
                <TextBlock as="span">{statusLabel(detail.status)}</TextBlock>
              </div>
            </div>
          </div>

          {/* Initial Complaint if any */}
          {detail.initial_complaint && (
            <div className="p-3 bg-muted/40 rounded-lg border border-border/40 text-xs">
              <TextBlock className="font-semibold text-ink block mb-0.5">Keluhan Awal Klien:</TextBlock>
              <TextBlock className="text-muted-foreground">{detail.initial_complaint}</TextBlock>
            </div>
          )}

          {/* Main Content Grid: Survey Points & Maps (Left/Center) vs Locked Tasks & BOM (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Left/Center Panel: Survey Findings + Embedded Satellite Map */}
            <div className="lg:col-span-8 space-y-4">
              {/* Interactive Satellite Map Section */}
              {activeTab !== "list" && (
                <div className="rounded-xl border border-line bg-surface overflow-hidden shadow-card">
                  <div className="p-3 border-b border-line bg-muted/30 flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-sm font-semibold text-ink">
                      <MapPin className="h-4 w-4 text-primary" />
                      <TextBlock as="span">
                        Peta Titik Pemasangan ({validCoords.length} dari {detail.survey_points?.length || 0} berkoordinat)
                      </TextBlock>
                    </div>
                    <TextBlock className="text-xs text-mist">
                      Klik penanda untuk melihat foto dan rekomendasi
                    </TextBlock>
                  </div>

                  {tileFailed && (
                    <TextBlock role="alert" className="text-sm text-warning">
          Gambar peta tidak bisa dimuat. Periksa sambungan internet, lalu coba lagi nanti.
        </TextBlock>
                  )}
                  <div className="h-[380px] w-full relative">
                    {validCoords.length > 0 ? (
                      <MapContainer
                        center={validCoords[0]}
                        zoom={17}
                        maxZoom={19}
                        scrollWheelZoom={false}
                        className="h-full w-full"
                      >
                        <TileLayer url={SAT_URL} attribution={SAT_ATTR} maxZoom={19} maxNativeZoom={18} eventHandlers={{ tileerror: () => setTileFailed(true) }} />
                        <FitSurveyMap coords={validCoords} />
                        {detail.survey_points?.map((pt, idx) => {
                          if (pt.site_lat == null || pt.site_lng == null) return null;
                          const pos: [number, number] = [Number(pt.site_lat), Number(pt.site_lng)];
                          return (
                            <Marker key={pt.point_id || idx} position={pos} icon={createSurveyPin(idx + 1)} eventHandlers={{ popupopen: indonesianCloseButton }}>
                              <Popup className="vms-map-popup">
                                <div className="w-56 p-1 space-y-1.5 text-ink">
                                  <div className="font-bold text-xs"><TextBlock as="span">{idx + 1}. {pt.point_name}</TextBlock></div>
                                  {pt.location_detail && (
                                    <div className="text-xs text-muted-foreground">{pt.location_detail}</div>
                                  )}
                                  <div className="text-xs text-primary font-medium">
                                    <TextBlock as="span">{pos[0].toFixed(5)}, {pos[1].toFixed(5)}</TextBlock>
                                  </div>
                                  {pt.recommended_work_type_name && (
                                    <div className="text-xs font-semibold bg-primary/10 text-primary px-1.5 py-0.5 rounded inline-block">
                                      {pt.recommended_work_type_name}
                                    </div>
                                  )}
                                  <PointPhotoThumb photo={pt.photos?.[0]} onOpen={setSelectedPhoto} />
                                </div>
                              </Popup>
                            </Marker>
                          );
                        })}
                      </MapContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center p-6 text-center bg-muted/10">
                        <div className="space-y-1">
                          <MapPin className="h-8 w-8 text-muted-foreground mx-auto" />
                          <TextBlock className="text-sm font-semibold text-ink">Peta Tidak Tersedia</TextBlock>
                          <TextBlock className="text-xs text-muted-foreground">
                            Titik survei belum memiliki data koordinat GPS dari surveyor lapangan.
                          </TextBlock>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Point Cards & Photo Previews Section */}
              {activeTab !== "map" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between pb-1">
                    <div className="text-sm font-semibold text-ink flex items-center gap-1.5">
                      <Camera className="h-4 w-4 text-primary" />
                      <TextBlock as="span">Daftar Titik dan Foto Dokumentasi Lapangan</TextBlock>
                    </div>
                    <TextBlock className="text-xs text-muted-foreground">
                      Total: {detail.survey_points?.length || 0} Titik
                    </TextBlock>
                  </div>

                  {(!detail.survey_points || detail.survey_points.length === 0) ? (
                    <div className="p-8 text-center border border-dashed rounded-xl bg-card">
                      <TextBlock className="text-sm text-muted-foreground">
                        Belum ada titik survei yang disubmit oleh tim lapangan.
                      </TextBlock>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
                      {detail.survey_points.map((pt, idx) => (
                        <div
                          key={pt.point_id || idx}
                          className="p-4 rounded-xl border border-border bg-card/60 space-y-3 hover:border-primary/40 transition-all shadow-xs"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-start gap-2.5">
                              <div className="h-6 w-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                                <TextBlock as="span">{idx + 1}</TextBlock>
                              </div>
                              <div>
                                <TextBlock className="text-sm font-bold text-ink">{pt.point_name}</TextBlock>
                                {pt.location_detail && (
                                  <div className="text-xs text-muted-foreground mt-0.5">
                                    <TextBlock as="span">{pt.location_detail}</TextBlock>
                                  </div>
                                )}
                              </div>
                            </div>

                            {pt.site_lat && pt.site_lng && (
                              <ActionButton
                                type="button"
                                variant="outline"
                                size="xs"
                                onClick={() => window.open(`https://maps.google.com/?q=${pt.site_lat},${pt.site_lng}`, "_blank")}
                                className="text-xs font-medium text-primary flex items-center gap-1 px-2.5 py-1 rounded-lg border-primary/30 h-auto"
                              >
                                <MapPin className="h-3 w-3" />
                                <TextBlock as="span">
                                  {Number(pt.site_lat).toFixed(5)}, {Number(pt.site_lng).toFixed(5)}
                                </TextBlock>
                              </ActionButton>
                            )}
                          </div>

                          {pt.recommended_work_type_name && (
                            <div className="pl-8 flex items-center gap-2">
                              <TextBlock as="span" className="text-xs text-muted-foreground">Rekomendasi Pekerjaan:</TextBlock>
                              <div className="text-xs font-semibold px-2.5 py-0.5 bg-blue-500/10 text-blue-600 dark:text-blue-400 rounded-md border border-blue-500/20">
                                <TextBlock as="span">{pt.recommended_work_type_name}</TextBlock>
                              </div>
                            </div>
                          )}

                          {pt.remarks && (
                            <div className="pl-8 text-xs bg-muted/40 p-2.5 rounded-lg text-muted-foreground border border-border/30">
                              <TextBlock as="span" className="font-semibold text-ink">Catatan Surveyor: </TextBlock>
                              <TextBlock as="span">{pt.remarks}</TextBlock>
                            </div>
                          )}

                          {/* Photos Gallery */}
                          {pt.photos && pt.photos.length > 0 && (
                            <div className="pl-8 space-y-1.5">
                              <div className="text-xs font-semibold text-ink flex items-center gap-1.5">
                                <Camera className="h-3.5 w-3.5 text-muted-foreground" />
                                <TextBlock as="span">Foto Dokumentasi Titik ({pt.photos.length} Foto)</TextBlock>
                              </div>
                              <div className="flex flex-wrap gap-2.5 pt-1">
                                {pt.photos.map((p, pIdx) => (
                                  <PointPhotoTile key={pIdx} photo={p} onOpen={setSelectedPhoto} />
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right Panel: Tasks, BOM, and Approval Lock */}
            <div className="lg:col-span-4 space-y-4">
              <div className="bg-surface-elevated/60 p-4 rounded-xl border border-border space-y-4 shadow-card">
                <div className="pb-2.5 border-b border-border">
                  <div className="text-sm font-bold text-ink flex items-center gap-1.5">
                    <Layers className="h-4 w-4 text-emerald-500" />
                    <TextBlock as="span">Daftar Tugas dan Kebutuhan Material</TextBlock>
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    <TextBlock as="span">
                      {isPendingApproval
                        ? "Preview otomatis yang akan dikunci saat persetujuan"
                        : "Daftar tugas resmi yang sudah dikunci"}
                    </TextBlock>
                  </div>
                </div>

                {/* Items Section */}
                <div className="space-y-2">
                  <TextBlock className="text-xs font-bold uppercase tracking-wider text-mist">
                    Item Tugas Lapangan ({detail.items?.length || detail.survey_points?.length || 0})
                  </TextBlock>

                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {isPendingApproval ? (
                      detail.survey_points?.map((pt, i) => (
                        <div
                          key={i}
                          className="text-xs p-2.5 rounded-lg bg-card border border-border flex items-center justify-between"
                        >
                          <div>
                            <TextBlock className="font-semibold text-ink">{pt.point_name}</TextBlock>
                            <div className="text-xs text-muted-foreground">
                              <TextBlock as="span">{pt.recommended_work_type_name || "Pekerjaan Standar"}</TextBlock>
                            </div>
                          </div>
                          <div className="text-xs font-bold text-primary px-2 py-0.5 bg-primary/10 rounded-md">
                            <TextBlock as="span">Target: 1 Titik</TextBlock>
                          </div>
                        </div>
                      ))
                    ) : (
                      detail.items?.map((item) => (
                        <div
                          key={item.item_id}
                          className="text-xs p-2.5 rounded-lg bg-card border border-border flex items-center justify-between"
                        >
                          <div>
                            <TextBlock className="font-semibold text-ink">{item.title}</TextBlock>
                            <div className="text-xs text-muted-foreground">
                              <TextBlock as="span">{item.work_type_name || "Jenis Pekerjaan"}</TextBlock>
                            </div>
                          </div>
                          <div
                            className={`text-xs font-bold px-2 py-0.5 rounded-md ${
                              item.status === "DONE"
                                ? "bg-emerald-500/10 text-emerald-500"
                                : item.status === "IN_PROGRESS"
                                ? "bg-blue-500/10 text-blue-500"
                                : "bg-muted text-muted-foreground"
                            }`}
                          >
                            <TextBlock as="span">{item.completed_qty} / {item.target_qty}</TextBlock>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* BOM Section */}
                <div className="space-y-2 pt-3 border-t border-border">
                  <div className="text-xs font-bold uppercase tracking-wider text-mist flex items-center gap-1.5">
                    <Package className="h-3.5 w-3.5" />
                    <TextBlock as="span">Kebutuhan Material (BOM)</TextBlock>
                  </div>

                  {isPendingApproval ? (
                    <div className="p-3 rounded-lg bg-muted/40 border border-border/50 text-xs text-muted-foreground">
                      <TextBlock as="span">
                        Material standar akan disalin secara otomatis dari Master Jenis Pekerjaan dan usulan surveyor pada setiap titik.
                      </TextBlock>
                    </div>
                  ) : (
                    <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                      {detail.bom?.map((b) => (
                        <div
                          key={b.bom_id}
                          className="text-xs p-2 rounded-lg bg-card/60 border border-border flex items-center justify-between"
                        >
                          <TextBlock as="span" className="text-ink font-semibold">{b.item_name}</TextBlock>
                          <TextBlock as="span" className="text-muted-foreground font-medium">
                            {b.actual_qty} / {b.estimated_qty} {b.unit}
                          </TextBlock>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Unduh Dokumen Resmi */}
                <div className="space-y-2 pt-3 border-t border-border">
                  <div className="text-xs font-bold uppercase tracking-wider text-mist flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <Download className="h-3.5 w-3.5 text-primary" />
                      <TextBlock as="span">Unduh Dokumen Resmi</TextBlock>
                    </div>
                    <TextBlock className="text-xs text-muted-foreground font-normal">KOP Logo Visiontech</TextBlock>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {detail.status === "BAST_SIGNED" && <BastDownloadButtons id={detail.work_order_id} number={detail.wo_number} />}
                    <ActionButton
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => downloadWorkOrderExport(detail.work_order_id, "survey", `Survei_${detail.wo_number}.docx`)}
                      className="text-xs justify-start h-11 px-2 bg-card hover:bg-surface-elevated"
                    >
                      <Download className="h-3 w-3 mr-1.5 text-amber-500 shrink-0" />
                      <TextBlock as="span" className="truncate">Laporan survei (.docx)</TextBlock>
                    </ActionButton>
                    <ActionButton
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => downloadWorkOrderExport(detail.work_order_id, "order", `Surat_Tugas_${detail.wo_number}.docx`)}
                      className="text-xs justify-start h-11 px-2 bg-card hover:bg-surface-elevated"
                    >
                      <Download className="h-3 w-3 mr-1.5 text-purple-500 shrink-0" />
                      <TextBlock as="span" className="truncate">Tugas (.docx)</TextBlock>
                    </ActionButton>
                    <ActionButton
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => downloadWorkOrderExport(detail.work_order_id, "boq", `BOQ_${detail.wo_number}.xlsx`)}
                      className="text-xs justify-start h-11 px-2 bg-card hover:bg-surface-elevated"
                    >
                      <Download className="h-3 w-3 mr-1.5 text-emerald-500 shrink-0" />
                      <TextBlock as="span" className="truncate">Daftar material (.xlsx)</TextBlock>
                    </ActionButton>
                    <ActionButton
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => downloadWorkOrderExport(detail.work_order_id, "slides", `Slide_Kemajuan_Pekerjaan_${detail.wo_number}.pptx`)}
                      className="text-xs justify-start h-11 px-2 bg-card hover:bg-surface-elevated"
                    >
                      <Download className="h-3 w-3 mr-1.5 text-orange-500 shrink-0" />
                      <TextBlock as="span" className="truncate">Slide (.pptx)</TextBlock>
                    </ActionButton>
                  </div>
                </div>

                {/* Approval Notice & Action */}
                {isPendingApproval && (
                  <div className="pt-2 border-t border-border space-y-3">
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl space-y-2">
                      <div className="flex gap-2 text-xs">
                        <FileCheck2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                        <div>
                          <TextBlock className="font-bold text-emerald-700 dark:text-emerald-300">
                            Persetujuan hasil survei
                          </TextBlock>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            <TextBlock as="span">
                              Mengunci titik survei, menyalin tugas ke jadwal harian, dan mengubah status menjadi{" "}
                            </TextBlock>
                            <TextBlock as="span" className="font-bold text-ink">{statusLabel("READY_TO_EXECUTE")}</TextBlock>
                            <TextBlock as="span">.</TextBlock>
                          </div>
                        </div>
                      </div>

                      <SurveyApproveButton pending={applyMutation.isPending} onApprove={handleApply} />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Photo Preview Lightbox */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setSelectedPhoto(null)}
        >
          <div className="max-w-4xl max-h-[88vh] relative bg-card p-2 rounded-2xl shadow-2xl">
            <div
              className="w-[80vw] max-w-[800px] h-[75vh] rounded-xl bg-contain bg-no-repeat bg-center"
              style={{ backgroundImage: `url(${selectedPhoto})` }}
            />
            <ActionButton
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setSelectedPhoto(null)}
              className="absolute -top-3 -right-3 size-11 rounded-full bg-surface text-ink font-bold shadow-lg flex items-center justify-center p-0 border border-line"
            >
              <X className="h-5 w-5" />
            </ActionButton>
          </div>
        </div>
      )}
    </VmsDialog>
  );
}
