import { useEffect, useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/stores/sessionStore";
import {
  fetchActiveHsePopup,
  acknowledgeHseCampaign,
  type HseCampaign,
} from "@/services/hseService";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ImageView } from "@/components/molecules/ImageView";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ShieldAlert, Clock, CheckCircle2 } from "@/components/molecules/Glyphs";
import { htmlToText } from "@/lib/htmlToText";
import { toast } from "sonner";

export function HseMandatoryPopupGate() {
  const { me } = useSession();
  const queryClient = useQueryClient();
  const startTimeRef = useRef<number>(0);

  // Ambil popup kampanye K3 yang aktif untuk pengguna saat ini
  const { data: campaign, isLoading, isError } = useQuery<HseCampaign | null>({
    queryKey: ["hse", "active-popup", me?.user_id],
    queryFn: () => (me ? fetchActiveHsePopup() : Promise.resolve(null)),
    enabled: Boolean(me),
    staleTime: 60 * 1000,
  });

  useEffect(() => {
    if (isError) toast.error("Gagal memuat panduan keselamatan kerja (K3/HSE).");
  }, [isError]);

  // Saat kampanye muncul, catat waktu mulai dan jalankan hitung mundur (turunan dari detik berlalu)
  const [tick, setTick] = useState<{ id: string; n: number }>({ id: "", n: 0 });
  const campaignId = campaign?.id;
  const cooldownTotal = campaign?.cooldown_seconds || 0;
  useEffect(() => {
    if (!campaignId) return;
    startTimeRef.current = Date.now();
    if (cooldownTotal <= 0) return;
    let n = 0;
    const interval = setInterval(() => {
      n += 1;
      setTick({ id: campaignId, n });
      if (n >= cooldownTotal) clearInterval(interval);
    }, 1000);
    return () => clearInterval(interval);
  }, [campaignId, cooldownTotal]);
  const remainingCooldown = campaignId
    ? Math.max(0, cooldownTotal - (tick.id === campaignId ? tick.n : 0))
    : 0;

  // Mutasi konfirmasi baca kampanye keselamatan
  const ackMutation = useMutation({
    mutationFn: async () => {
      if (!campaign) return;
      const readSeconds = Math.max(
        1,
        Math.round((Date.now() - (startTimeRef.current || Date.now())) / 1000)
      );
      await acknowledgeHseCampaign(
        campaign.id,
        readSeconds,
        `Web Browser (${navigator.userAgent.slice(0, 80)})`
      );
    },
    onSuccess: () => {
      toast.success("Terima kasih telah membaca panduan keselamatan kerja (K3/HSE).");
      queryClient.setQueryData(["hse", "active-popup", me?.user_id], null);
    },
    onError: () => {
      toast.error("Gagal mengonfirmasi pembacaan kampanye. Coba lagi.");
    },
  });

  if (isLoading || !campaign) return null;

  const isButtonDisabled = remainingCooldown > 0 || ackMutation.isPending;

  return (
    <VmsDialog
      open={true}
      title="PANDUAN KESELAMATAN KERJA (K3 / HSE)"
      size="xl"
      onClose={() => {
        // Non-skippable: dialog tidak bisa ditutup sebelum membaca dan klik konfirmasi
      }}
      footer={
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 w-full">
          <div className="text-xs text-mist flex items-center gap-1.5 self-start sm:self-center">
            {remainingCooldown > 0 ? (
              <>
                <Clock className="h-4 w-4 text-amber-500 animate-pulse" />
                <TextBlock as="span" className="font-semibold text-amber-600">
                  Wajib membaca selama {remainingCooldown} detik lagi
                </TextBlock>
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                <TextBlock as="span" className="font-medium text-emerald-600">
                  Waktu baca selesai, silakan konfirmasi
                </TextBlock>
              </>
            )}
          </div>

          <ActionButton
            variant="default"
            disabled={isButtonDisabled}
            onClick={() => ackMutation.mutate()}
            className="w-full sm:w-auto font-semibold px-6 h-11"
          >
            <TextBlock as="span">
              {ackMutation.isPending
                ? "Menyimpan konfirmasi..."
                : remainingCooldown > 0
                ? `Tunggu (${remainingCooldown}s)`
                : "Saya Telah Membaca dan Memahami Panduan Ini"}
            </TextBlock>
          </ActionButton>
        </div>
      }
    >
      <div className="space-y-4 pt-1 pb-2">
        <div className="flex items-center gap-3 p-3 bg-amber-500/10 rounded-xl border border-amber-500/20">
          <ShieldAlert className="h-6 w-6 text-amber-600 shrink-0" />
          <div>
            <div className="flex items-center gap-2">
              <TextBlock as="span" className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[11px] font-bold text-amber-700">
                KAMPANYE KESELAMATAN
              </TextBlock>
              {campaign.target_audience !== "ALL" && (
                <TextBlock as="span" className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
                  Sasaran: {campaign.target_audience}
                </TextBlock>
              )}
            </div>
            <TextBlock className="font-bold text-ink text-base mt-0.5">
              {campaign.title}
            </TextBlock>
          </div>
        </div>

        {campaign.media_url && (
          <div className="overflow-hidden rounded-xl border border-line bg-surface-elevated">
            <ImageView
              src={campaign.media_url}
              alt={campaign.title}
              className="max-h-64 w-full object-cover"
            />
          </div>
        )}

        <div className="whitespace-pre-line rounded-xl bg-surface-elevated/60 p-4 border border-line/60 text-sm leading-relaxed text-ink">
          {htmlToText(campaign.content_body)}
        </div>

        <div className="rounded-xl border border-primary/20 bg-primary/5 p-3.5 text-xs text-mist flex items-start gap-2.5">
          <ShieldAlert className="h-4 w-4 shrink-0 text-primary mt-0.5" />
          <TextBlock as="p">
            Demi keselamatan kerja seluruh tim Visiontech di kantor maupun di lokasi proyek lapangan,
            setiap anggota wajib membaca dan mematuhi panduan K3 ini sebelum melanjutkan pekerjaan di sistem.
          </TextBlock>
        </div>
      </div>
    </VmsDialog>
  );
}
