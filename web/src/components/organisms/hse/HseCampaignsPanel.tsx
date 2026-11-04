import { useState, type ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchHseCampaigns,
  createHseCampaign,
  fetchCampaignReaders,
  fetchVehicleInspections,
  verifyVehicleInspection,
  type HseCampaign,
  type CampaignReader,
  type VehicleInspection,
} from "@/services/hseService";
import { PlainAction } from "@/components/molecules/PlainAction";
import { ControlLabel, ControlInput, ControlSelect, ControlOption, ControlTextarea } from "@/components/molecules/FormBlock";
import { TableBlock, TableBlockHead, TableBlockBody, TableBlockRow, TableBlockHeaderCell, TableBlockCell } from "@/components/molecules/TableBlock";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import {
  ShieldCheck,
  Plus,
  Eye,
  Truck,
  CheckCircle2,
  AlertCircle,
} from "@/components/molecules/Glyphs";
import { htmlToText } from "@/lib/htmlToText";
import { toast } from "sonner";
import { formatDateTime } from "@/lib/format";

export function HseCampaignsPanel({ renderPage }: { renderPage: (page: { action: ReactNode; body: ReactNode }) => ReactNode }) {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"campaigns" | "inspections">("campaigns");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedCampaignForAudit, setSelectedCampaignForAudit] = useState<HseCampaign | null>(null);

  // Form State Buat Kampanye
  const [title, setTitle] = useState("");
  const [contentBody, setContentBody] = useState("");
  const [targetAudience, setTargetAudience] = useState<"ALL" | "FIELD" | "OFFICE">("ALL");
  const [mediaUrl, setMediaUrl] = useState("");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState(() =>
    new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString().slice(0, 10)
  );
  const [isMandatory, setIsMandatory] = useState(true);
  const [cooldownSeconds, setCooldownSeconds] = useState(5);

  // Query Kampanye K3
  const { data: campaigns = [], isLoading: isLoadingCampaigns } = useQuery<HseCampaign[]>({
    queryKey: ["hse", "campaigns"],
    queryFn: fetchHseCampaigns,
  });

  // Query Audit Pembaca untuk kampanye terpilih
  const { data: readers = [], isLoading: isLoadingReaders } = useQuery<CampaignReader[]>({
    queryKey: ["hse", "campaign-readers", selectedCampaignForAudit?.id],
    queryFn: () => (selectedCampaignForAudit ? fetchCampaignReaders(selectedCampaignForAudit.id) : Promise.resolve([])),
    enabled: Boolean(selectedCampaignForAudit),
  });

  // Query Inspeksi Kendaraan
  const { data: inspections = [], isLoading: isLoadingInspections } = useQuery<VehicleInspection[]>({
    queryKey: ["hse", "inspections"],
    queryFn: fetchVehicleInspections,
  });

  // Mutasi Buat Kampanye
  const createMutation = useMutation({
    mutationFn: () =>
      createHseCampaign({
        title,
        content_body: contentBody,
        target_audience: targetAudience,
        media_url: mediaUrl || null,
        start_date: startDate,
        end_date: endDate,
        is_mandatory: isMandatory,
        cooldown_seconds: Number(cooldownSeconds),
      }),
    onSuccess: () => {
      toast.success("Kampanye K3/HSE berhasil diterbitkan!");
      setIsCreateOpen(false);
      setTitle("");
      setContentBody("");
      setMediaUrl("");
      queryClient.invalidateQueries({ queryKey: ["hse", "campaigns"] });
    },
    onError: () => {
      toast.error("Gagal menerbitkan kampanye keselamatan. Periksa data kembali.");
    },
  });

  // Mutasi Verifikasi Inspeksi
  const verifyInspectionMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      verifyVehicleInspection(id, notes),
    onSuccess: () => {
      toast.success("Inspeksi kendaraan berhasil diverifikasi oleh HSE!");
      queryClient.invalidateQueries({ queryKey: ["hse", "inspections"] });
    },
    onError: () => {
      toast.error("Gagal memverifikasi inspeksi.");
    },
  });

  const action = activeTab === "campaigns" ? (
    <ActionButton
      variant="default"
      size="sm"
      onClick={() => setIsCreateOpen(true)}
      className="flex items-center gap-1.5"
    >
      <Plus size={16} />
      <TextBlock as="span">Terbitkan Kampanye K3</TextBlock>
    </ActionButton>
  ) : null;

  const body = (
    <>
      {/* Tab Navigasi */}
      <div className="flex border-b border-line mb-6 gap-6">
        <PlainAction
          type="button"
          onClick={() => setActiveTab("campaigns")}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "campaigns"
              ? "border-primary text-primary"
              : "border-transparent text-mist hover:text-ink"
          }`}
        >
          <ShieldCheck size={18} />
          <TextBlock as="span">Kampanye & Pengumuman K3 ({campaigns.length})</TextBlock>
        </PlainAction>
        <PlainAction
          type="button"
          onClick={() => setActiveTab("inspections")}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "inspections"
              ? "border-primary text-primary"
              : "border-transparent text-mist hover:text-ink"
          }`}
        >
          <Truck size={18} />
          <TextBlock as="span">Inspeksi Kendaraan ({inspections.length})</TextBlock>
        </PlainAction>
      </div>

      {/* Konten Tab 1: Kampanye K3 */}
      {activeTab === "campaigns" && (
        <div className="space-y-4">
          {isLoadingCampaigns ? (
            <div className="py-12 text-center text-mist"><TextBlock as="span">Memuat kampanye K3...</TextBlock></div>
          ) : campaigns.length === 0 ? (
            <div className="rounded-2xl border border-line bg-surface p-10 text-center">
              <ShieldCheck className="mx-auto h-12 w-12 text-mist mb-3" />
              <TextBlock className="font-semibold text-ink text-base">
                Belum ada kampanye keselamatan kerja aktif
              </TextBlock>
              <TextBlock className="text-sm text-mist mt-1 max-w-md mx-auto">
                Terbitkan kampanye keselamatan agar muncul otomatis di aplikasi teknisi lapangan dan portal kantor saat login.
              </TextBlock>
              <ActionButton
                variant="outline"
                size="sm"
                onClick={() => setIsCreateOpen(true)}
                className="mt-4"
              >
                <TextBlock as="span">Buat Kampanye Pertama</TextBlock>
              </ActionButton>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {campaigns.map((c) => (
                <div
                  key={c.id}
                  className="rounded-2xl border border-line bg-surface p-5 shadow-xs flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <TextBlock as="span" className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-bold text-amber-600">
                        {c.target_audience === "ALL"
                          ? "Semua Pengguna"
                          : c.target_audience === "FIELD"
                          ? "Teknisi Lapangan"
                          : c.target_audience === "INDIVIDUAL"
                          ? "Pengguna Tertentu"
                          : "Karyawan Kantor"}
                      </TextBlock>
                      {c.is_mandatory && (
                        <TextBlock as="span" className="rounded-full bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold text-rose-600">
                          Wajib Baca ({c.cooldown_seconds}s)
                        </TextBlock>
                      )}
                    </div>

                    <TextBlock className="font-bold text-ink text-base line-clamp-1">
                      {c.title}
                    </TextBlock>
                    <TextBlock className="text-xs text-mist mt-1 line-clamp-3 whitespace-pre-line">
                      {htmlToText(c.content_body)}
                    </TextBlock>
                  </div>

                  <div className="mt-5 pt-3 border-t border-line flex items-center justify-between">
                    <TextBlock as="span" className="text-[11px] text-mist">
                      {c.start_date} s/d {c.end_date}
                    </TextBlock>
                    <ActionButton
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedCampaignForAudit(c)}
                      className="text-xs flex items-center gap-1.5"
                    >
                      <Eye size={14} />
                      <TextBlock as="span">Audit Pembaca</TextBlock>
                    </ActionButton>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Konten Tab 2: Inspeksi Kendaraan */}
      {activeTab === "inspections" && (
        <div className="space-y-4">
          {isLoadingInspections ? (
            <div className="py-12 text-center text-mist"><TextBlock as="span">Memuat data inspeksi kendaraan...</TextBlock></div>
          ) : inspections.length === 0 ? (
            <div className="rounded-2xl border border-line bg-surface p-10 text-center">
              <Truck className="mx-auto h-12 w-12 text-mist mb-3" />
              <TextBlock className="font-semibold text-ink text-base">
                Belum ada data inspeksi kendaraan
              </TextBlock>
              <TextBlock className="text-sm text-mist mt-1">
                Laporan pemeriksaan berkala dan harian kendaraan armada akan tampil di sini untuk diverifikasi oleh tim HSE.
              </TextBlock>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-line bg-surface">
              <TableBlock className="w-full text-left text-sm">
                <TableBlockHead className="bg-surface-elevated border-b border-line text-xs uppercase tracking-wider text-mist">
                  <TableBlockRow>
                    <TableBlockHeaderCell className="p-3.5">Kendaraan</TableBlockHeaderCell>
                    <TableBlockHeaderCell className="p-3.5">Tipe & Tanggal</TableBlockHeaderCell>
                    <TableBlockHeaderCell className="p-3.5">Pemeriksa</TableBlockHeaderCell>
                    <TableBlockHeaderCell className="p-3.5">Kondisi</TableBlockHeaderCell>
                    <TableBlockHeaderCell className="p-3.5">Verifikasi HSE</TableBlockHeaderCell>
                    <TableBlockHeaderCell className="p-3.5 text-right">Aksi</TableBlockHeaderCell>
                  </TableBlockRow>
                </TableBlockHead>
                <TableBlockBody className="divide-y divide-line">
                  {inspections.map((insp) => {
                    const isVerified = insp.status === "VERIFIED";
                    const isRejected = insp.status === "REJECTED";
                    return (
                      <TableBlockRow key={insp.id} className="hover:bg-surface-elevated/40">
                      <TableBlockCell className="p-3.5">
                        <div className="font-semibold text-ink">{insp.asset_name}</div>
                        <div className="text-xs text-mist">{insp.plate_number || "-"}</div>
                      </TableBlockCell>
                      <TableBlockCell className="p-3.5">
                        <div className="font-medium text-ink">{insp.inspection_type}</div>
                        <div className="text-xs text-mist">{insp.inspection_date}</div>
                      </TableBlockCell>
                      <TableBlockCell className="p-3.5 text-ink">{insp.inspector_name}</TableBlockCell>
                      <TableBlockCell className="p-3.5">
                        <TextBlock as="span"
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            isVerified
                              ? "bg-emerald-500/10 text-emerald-600"
                              : isRejected
                              ? "bg-rose-500/10 text-rose-600"
                              : "bg-amber-500/10 text-amber-600"
                          }`}
                        >
                          {isVerified ? (
                            <CheckCircle2 size={12} />
                          ) : (
                            <AlertCircle size={12} />
                          )}
                          {isVerified
                            ? "Terverifikasi"
                            : isRejected
                            ? "Ditolak"
                            : insp.status === "SUBMITTED"
                            ? "Menunggu Verifikasi"
                            : insp.status}
                        </TextBlock>
                      </TableBlockCell>
                      <TableBlockCell className="p-3.5">
                        {insp.is_verified_by_hse ? (
                          <div
                            className={`text-xs font-medium flex items-center gap-1 ${
                              isRejected ? "text-rose-600" : "text-emerald-600"
                            }`}
                          >
                            <CheckCircle2 size={14} />
                            <TextBlock as="span">
                              {isRejected ? "Ditolak" : "Diverifikasi"} {insp.verified_by_name}
                            </TextBlock>
                          </div>
                        ) : (
                          <TextBlock as="span" className="text-xs text-amber-600 font-medium">Menunggu Verifikasi</TextBlock>
                        )}
                      </TableBlockCell>
                      <TableBlockCell className="p-3.5 text-right">
                        {!insp.is_verified_by_hse && (
                          <ActionButton
                            variant="default"
                            size="sm"
                            disabled={verifyInspectionMutation.isPending}
                            onClick={() =>
                              verifyInspectionMutation.mutate({
                                id: insp.id,
                                notes: "Disetujui aman oleh tim HSE",
                              })
                            }
                            className="text-xs"
                          >
                            <TextBlock as="span">Verifikasi</TextBlock>
                          </ActionButton>
                        )}
                      </TableBlockCell>
                      </TableBlockRow>
                    );
                  })}
                </TableBlockBody>
              </TableBlock>
            </div>
          )}
        </div>
      )}

      {/* Modal Buat Kampanye K3 */}
      {isCreateOpen && (
        <VmsDialog
          open={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          title="Terbitkan Kampanye Keselamatan Kerja (HSE)"
          size="xl"
          footer={
            <div className="flex justify-end gap-2 w-full">
              <ActionButton
                variant="outline"
                onClick={() => setIsCreateOpen(false)}
                disabled={createMutation.isPending}
              >
                <TextBlock as="span">Batal</TextBlock>
              </ActionButton>
              <ActionButton
                variant="default"
                disabled={!title || !contentBody || createMutation.isPending}
                onClick={() => createMutation.mutate()}
              >
                <TextBlock as="span">
                  {createMutation.isPending ? "Menerbitkan..." : "Terbitkan Kampanye"}
                </TextBlock>
              </ActionButton>
            </div>
          }
        >
          <div className="space-y-4 pt-2">
            <div>
              <ControlLabel className="block text-xs font-semibold uppercase tracking-wider text-mist mb-1">
                Judul Kampanye Keselamatan *
              </ControlLabel>
              <ControlInput
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Contoh: Kewajiban Penggunaan Helm & Body Harness di Tiang"
                className="w-full rounded-xl border border-line bg-surface p-3 text-sm outline-none focus:border-primary"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <ControlLabel className="block text-xs font-semibold uppercase tracking-wider text-mist mb-1">
                  Target Audiens *
                </ControlLabel>
                <ControlSelect
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value as "ALL" | "FIELD" | "OFFICE")}
                  className="w-full rounded-xl border border-line bg-surface p-3 text-sm outline-none focus:border-primary"
                >
                  <ControlOption value="ALL">Semua Karyawan (Kantor & Lapangan)</ControlOption>
                  <ControlOption value="FIELD">Khusus Teknisi Lapangan</ControlOption>
                  <ControlOption value="OFFICE">Khusus Karyawan Kantor</ControlOption>
                </ControlSelect>
              </div>

              <div>
                <ControlLabel className="block text-xs font-semibold uppercase tracking-wider text-mist mb-1">
                  Cooldown Wajib Baca (Detik)
                </ControlLabel>
                <ControlInput
                  type="number"
                  min="0"
                  max="60"
                  value={cooldownSeconds}
                  onChange={(e) => setCooldownSeconds(Number(e.target.value))}
                  className="w-full rounded-xl border border-line bg-surface p-3 text-sm outline-none focus:border-primary"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <ControlLabel className="block text-xs font-semibold uppercase tracking-wider text-mist mb-1">
                  Tanggal Mulai Muncul
                </ControlLabel>
                <ControlInput
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full rounded-xl border border-line bg-surface p-3 text-sm outline-none focus:border-primary"
                />
              </div>
              <div>
                <ControlLabel className="block text-xs font-semibold uppercase tracking-wider text-mist mb-1">
                  Tanggal Berakhir
                </ControlLabel>
                <ControlInput
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full rounded-xl border border-line bg-surface p-3 text-sm outline-none focus:border-primary"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <ControlInput
                type="checkbox"
                id="is_mandatory"
                checked={isMandatory}
                onChange={(e) => setIsMandatory(e.target.checked)}
                className="h-4 w-4 rounded border-line text-primary focus:ring-primary"
              />
              <ControlLabel htmlFor="is_mandatory" className="text-sm font-medium text-ink cursor-pointer">
                Wajibkan membaca saat pertama kali login (Non-skippable Popup Gate)
              </ControlLabel>
            </div>

            <div>
              <ControlLabel className="block text-xs font-semibold uppercase tracking-wider text-mist mb-1">
                URL Gambar / Poster Edukasi (Opsional)
              </ControlLabel>
              <ControlInput
                type="text"
                value={mediaUrl}
                onChange={(e) => setMediaUrl(e.target.value)}
                placeholder="https://..."
                className="w-full rounded-xl border border-line bg-surface p-3 text-sm outline-none focus:border-primary"
              />
            </div>

            <div>
              <ControlLabel className="block text-xs font-semibold uppercase tracking-wider text-mist mb-1">
                Isi Panduan Keselamatan *
              </ControlLabel>
              <ControlTextarea
                rows={5}
                value={contentBody}
                onChange={(e) => setContentBody(e.target.value)}
                placeholder="Tuliskan aturan keselamatan, bahaya yang harus diwaspadai, dan instruksi K3 lengkap..."
                className="w-full rounded-xl border border-line bg-surface p-3 text-sm outline-none focus:border-primary"
              />
            </div>
          </div>
        </VmsDialog>
      )}

      {/* Modal Audit Pembaca Kampanye */}
      {selectedCampaignForAudit && (
        <VmsDialog
          open={Boolean(selectedCampaignForAudit)}
          onClose={() => setSelectedCampaignForAudit(null)}
          title={`Audit Pembaca — ${selectedCampaignForAudit.title}`}
          size="2xl"
          footer={
            <div className="flex justify-end w-full">
              <ActionButton
                variant="outline"
                onClick={() => setSelectedCampaignForAudit(null)}
              >
                <TextBlock as="span">Tutup</TextBlock>
              </ActionButton>
            </div>
          }
        >
          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between p-3 bg-surface-elevated rounded-xl border border-line text-xs">
              <div>
                <TextBlock as="span" className="text-mist">Target: </TextBlock>
                <TextBlock as="span" className="font-semibold text-ink">{selectedCampaignForAudit.target_audience}</TextBlock>
              </div>
              <div>
                <TextBlock as="span" className="text-mist">Total Pembaca: </TextBlock>
                <TextBlock as="span" className="font-bold text-primary">{readers.length} Karyawan</TextBlock>
              </div>
            </div>

            {isLoadingReaders ? (
              <div className="py-12 text-center text-mist"><TextBlock as="span">Memuat daftar audit pembaca...</TextBlock></div>
            ) : readers.length === 0 ? (
              <div className="py-12 text-center text-mist"><TextBlock as="span">
                Belum ada pengguna yang membaca atau mengonfirmasi kampanye ini.
              </TextBlock></div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-line bg-surface">
                <TableBlock className="w-full text-left text-xs">
                  <TableBlockHead className="bg-surface-elevated border-b border-line uppercase tracking-wider text-mist">
                    <TableBlockRow>
                      <TableBlockHeaderCell className="p-3">Nama Karyawan</TableBlockHeaderCell>
                      <TableBlockHeaderCell className="p-3">Platform</TableBlockHeaderCell>
                      <TableBlockHeaderCell className="p-3">Waktu Konfirmasi</TableBlockHeaderCell>
                      <TableBlockHeaderCell className="p-3">Durasi Baca</TableBlockHeaderCell>
                      <TableBlockHeaderCell className="p-3">Perangkat</TableBlockHeaderCell>
                    </TableBlockRow>
                  </TableBlockHead>
                  <TableBlockBody className="divide-y divide-line">
                    {readers.map((r) => (
                      <TableBlockRow key={r.acknowledgment_id} className="hover:bg-surface-elevated/40">
                        <TableBlockCell className="p-3 font-semibold text-ink">
                          {r.user_name}
                          <div className="text-[11px] text-mist font-normal">{r.user_email}</div>
                        </TableBlockCell>
                        <TableBlockCell className="p-3">
                          <TextBlock as="span" className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                            {r.platform}
                          </TextBlock>
                        </TableBlockCell>
                        <TableBlockCell className="p-3 text-mist">{formatDateTime(r.acknowledged_at)}</TableBlockCell>
                        <TableBlockCell className="p-3 font-medium text-emerald-600">
                          {r.read_duration_seconds} detik
                        </TableBlockCell>
                        <TableBlockCell className="p-3 text-mist max-w-[200px] truncate" title={r.device_info || "-"}>
                          {r.device_info || "-"}
                        </TableBlockCell>
                      </TableBlockRow>
                    ))}
                  </TableBlockBody>
                </TableBlock>
              </div>
            )}
          </div>
        </VmsDialog>
      )}
    </>
  );

  return <>{renderPage({ action, body })}</>;
}
