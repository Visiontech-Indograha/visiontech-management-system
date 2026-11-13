import { useState, type ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchHseCampaigns,
  createHseCampaign,
  fetchCampaignReaders,
  archiveHseCampaign,
  deleteHseCampaign,
  type HseCampaign,
  type CampaignReader,
} from "@/services/hseService";
import { ControlLabel, ControlInput, ControlSelect, ControlOption, ControlTextarea } from "@/components/molecules/FormBlock";
import { TableBlock, TableBlockHead, TableBlockBody, TableBlockRow, TableBlockHeaderCell, TableBlockCell } from "@/components/molecules/TableBlock";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import {
  ShieldCheck,
  Plus,
  Eye,
} from "@/components/molecules/Glyphs";
import { htmlToText } from "@/lib/htmlToText";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { useSession } from "@/stores/sessionStore";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { uploadFiles } from "@/services/uploadService";
import { carouselConfigError, CAROUSEL_MAX_SECONDS } from "@/lib/hseCarousel";
import { campaignPublishBlocker, HSE_TITLE_MAX } from "@/lib/hseCampaignRules";
import { HseCampaignPhotosField, type CampaignPhotoDraft } from "@/components/organisms/hse/HseCampaignPhotosField";

export function HseCampaignsPanel({ renderPage }: { renderPage: (page: { action: ReactNode; body: ReactNode }) => ReactNode }) {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedCampaignForAudit, setSelectedCampaignForAudit] = useState<HseCampaign | null>(null);

  // Form State Buat Kampanye
  const { me } = useSession();
  const canManage = Boolean(me?.permissions?.includes("manage:hse_campaigns"));
  const [pendingAction, setPendingAction] = useState<{ kind: "archive" | "delete"; campaign: HseCampaign } | null>(null);
  const [titleError, setTitleError] = useState("");
  const [title, setTitle] = useState("");
  const [contentBody, setContentBody] = useState("");
  const [targetAudience, setTargetAudience] = useState<"ALL" | "FIELD" | "OFFICE">("ALL");
  const [photos, setPhotos] = useState<CampaignPhotoDraft[]>([]);
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState(() =>
    new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString().slice(0, 10)
  );
  const [isMandatory, setIsMandatory] = useState(true);
  const [cooldownSeconds, setCooldownSeconds] = useState(10);
  const publishBlocker = campaignPublishBlocker(title, contentBody);
  const configError = carouselConfigError(photos.length, Number(cooldownSeconds));

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

  // Mutasi Buat Kampanye
  const createMutation = useMutation({
    mutationFn: async () => {
      // Foto diunggah dulu (urutan dipertahankan), lalu kampanye diterbitkan dengan daftar id berkasnya.
      const mediaIds = photos.length > 0 ? await uploadFiles(photos.map((p) => p.file)) : [];
      return createHseCampaign({
        title,
        content_body: contentBody,
        target_audience: targetAudience,
        media_ids: mediaIds,
        media_captions: photos.map((p) => p.caption.trim()),
        start_date: startDate,
        end_date: endDate,
        is_mandatory: isMandatory,
        cooldown_seconds: Number(cooldownSeconds),
      });
    },
    onSuccess: () => {
      toast.success("Kampanye K3/HSE berhasil diterbitkan!");
      setIsCreateOpen(false);
      setTitle("");
      setContentBody("");
      setPhotos([]);
      queryClient.invalidateQueries({ queryKey: ["hse", "campaigns"] });
    },
    onError: (err) => {
      const setField = (name: string, e: { message: string }) => {
        if (name === "title") setTitleError(e.message);
      };
      if (applyFieldErrors(err, setField as never, ["title"])) return;
      toast.error(errorMessage(err, "Gagal menerbitkan kampanye keselamatan. Periksa data kembali."));
    },
  });

  const manageMutation = useMutation({
    mutationFn: ({ kind, campaign }: { kind: "archive" | "delete"; campaign: HseCampaign }) =>
      kind === "archive" ? archiveHseCampaign(campaign.id) : deleteHseCampaign(campaign.id),
    onSuccess: (_d, v) => {
      toast.success(v.kind === "archive" ? "Kampanye diarsipkan." : "Kampanye dihapus.");
      setPendingAction(null);
      queryClient.invalidateQueries({ queryKey: ["hse", "campaigns"] });
    },
    onError: (err) => toast.error(errorMessage(err, "Gagal memproses kampanye. Coba lagi.")),
  });

  const action = (
    <ActionButton
      variant="default"
      size="sm"
      onClick={() => setIsCreateOpen(true)}
      className="flex items-center gap-1.5"
    >
      <Plus size={16} />
      <TextBlock as="span">Terbitkan Kampanye K3</TextBlock>
    </ActionButton>
  );

  const body = (
    <>
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
                        <TextBlock as="span" className="rounded-full bg-rose-500/10 px-2 py-0.5 text-xs font-bold text-rose-600">
                          Wajib Baca ({c.cooldown_seconds}s)
                        </TextBlock>
                      )}
                    </div>

                    {!c.is_active && (
                      <TextBlock as="span" className="text-xs font-semibold text-mist">Diarsipkan</TextBlock>
                    )}
                    <TextBlock className="font-bold text-ink text-base line-clamp-1">
                      {c.title}
                    </TextBlock>
                    <TextBlock className="text-xs text-mist mt-1 line-clamp-3 whitespace-pre-line">
                      {htmlToText(c.content_body)}
                    </TextBlock>
                  </div>

                  <div className="mt-5 pt-3 border-t border-line flex items-center justify-between">
                    <TextBlock as="span" className="text-xs text-mist">
                      {c.start_date} s/d {c.end_date}
                    </TextBlock>
                    <div className="flex flex-wrap items-center justify-end gap-2">
                    {canManage && c.is_active && (
                      <ActionButton variant="outline" size="sm" onClick={() => setPendingAction({ kind: "archive", campaign: c })} className="text-xs">
                        <TextBlock as="span">Arsipkan</TextBlock>
                      </ActionButton>
                    )}
                    {canManage && (
                      <ActionButton variant="outline" size="sm" onClick={() => setPendingAction({ kind: "delete", campaign: c })} className="text-xs text-danger">
                        <TextBlock as="span">Hapus</TextBlock>
                      </ActionButton>
                    )}
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
                </div>
              ))}
            </div>
          )}
        </div>

      <ConfirmDialog
        open={pendingAction !== null}
        title={pendingAction?.kind === "delete" ? "Hapus kampanye ini?" : "Arsipkan kampanye ini?"}
        message={
          pendingAction?.kind === "delete"
            ? `Kampanye "${pendingAction.campaign.title}" akan dihapus dan tidak tampil lagi.`
            : `Kampanye "${pendingAction?.campaign.title ?? ""}" tidak akan tampil lagi ke karyawan. Riwayat pembaca tetap tersimpan.`
        }
        confirmLabel={pendingAction?.kind === "delete" ? "Ya, hapus" : "Ya, arsipkan"}
        danger={pendingAction?.kind === "delete"}
        busy={manageMutation.isPending}
        onConfirm={() => pendingAction && manageMutation.mutate(pendingAction)}
        onClose={() => setPendingAction(null)}
      />

      {/* Modal Buat Kampanye K3 */}
      {isCreateOpen && (
        <VmsDialog
          open={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          title="Terbitkan Kampanye Keselamatan Kerja (HSE)"
          size="xl"
          className="sm:w-[min(960px,94vw)] sm:max-w-[960px]"
          footer={
            <div className="flex flex-wrap items-center justify-end gap-2 w-full">
              {publishBlocker && (
                <TextBlock id="hse-publish-blocker" className="mr-auto text-xs text-mist">
                  {publishBlocker}
                </TextBlock>
              )}
              <ActionButton
                variant="outline"
                onClick={() => setIsCreateOpen(false)}
                disabled={createMutation.isPending}
              >
                <TextBlock as="span">Batal</TextBlock>
              </ActionButton>
              <ActionButton
                variant="default"
                disabled={publishBlocker !== null || createMutation.isPending || configError !== null}
                aria-describedby={publishBlocker ? "hse-publish-blocker" : undefined}
                onClick={() => {
                  setTitleError("");
                  createMutation.mutate();
                }}
              >
                <TextBlock as="span">
                  {createMutation.isPending ? "Menerbitkan..." : "Terbitkan Kampanye"}
                </TextBlock>
              </ActionButton>
            </div>
          }
        >
          <div className="grid grid-cols-1 gap-6 pt-2 lg:grid-cols-2">
          <div className="min-w-0 space-y-4">
            <div>
              <ControlLabel className="block text-xs font-semibold uppercase tracking-wider text-mist mb-1">
                Judul Kampanye Keselamatan *
              </ControlLabel>
              <ControlInput
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={HSE_TITLE_MAX}
                aria-invalid={titleError !== ""}
                placeholder="Contoh: Kewajiban Penggunaan Helm dan Body Harness di Tiang"
                className="w-full rounded-xl border border-line bg-surface p-3 text-sm outline-none focus:border-primary"
              />
              {titleError && (
                <TextBlock role="alert" className="mt-1 text-sm font-medium text-destructive">{titleError}</TextBlock>
              )}
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
                  <ControlOption value="ALL">Semua Karyawan (Kantor dan Lapangan)</ControlOption>
                  <ControlOption value="FIELD">Khusus Teknisi Lapangan</ControlOption>
                  <ControlOption value="OFFICE">Khusus Karyawan Kantor</ControlOption>
                </ControlSelect>
              </div>

              <div>
                <ControlLabel className="block text-xs font-semibold uppercase tracking-wider text-mist mb-1">
                  Durasi Baca Wajib (Detik)
                </ControlLabel>
                <ControlInput
                  type="number"
                  min={photos.length > 0 ? 10 : 0}
                  max={CAROUSEL_MAX_SECONDS}
                  value={cooldownSeconds}
                  aria-invalid={configError !== null}
                  aria-describedby="hse-duration-help"
                  onChange={(e) => setCooldownSeconds(Number(e.target.value))}
                  className="w-full rounded-xl border border-line bg-surface p-3 text-sm outline-none focus:border-primary"
                />
                <TextBlock
                  as="p"
                  id="hse-duration-help"
                  role={configError ? "alert" : undefined}
                  className={configError ? "mt-1 text-xs font-medium text-destructive" : "mt-1 text-xs text-mist"}
                >
                  {configError ?? "Tombol konfirmasi aktif setelah durasi ini. Dengan foto: 10-300 detik, minimal 3 detik per foto."}
                </TextBlock>
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
          <div className="min-w-0 space-y-4">
            <HseCampaignPhotosField
              photos={photos}
              onChange={setPhotos}
              durationSeconds={Number(cooldownSeconds)}
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
                          <div className="text-xs text-mist font-normal">{r.user_email}</div>
                        </TableBlockCell>
                        <TableBlockCell className="p-3">
                          <TextBlock as="span" className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
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
