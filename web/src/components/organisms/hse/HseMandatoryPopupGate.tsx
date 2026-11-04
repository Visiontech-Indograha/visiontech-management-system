import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/stores/sessionStore";
import {
  fetchActiveHsePopup,
  acknowledgeHseCampaign,
  markHseCampaignSeen,
  type HseCampaign,
} from "@/services/hseService";
import { fetchFileUrl } from "@/services/fileService";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ImageView } from "@/components/molecules/ImageView";
import { TextBlock } from "@/components/molecules/TextBlock";
import { CampaignMediaCarousel, type CarouselSlide } from "@/components/molecules/CampaignMediaCarousel";
import { ShieldAlert, Clock, CheckCircle2 } from "@/components/molecules/Glyphs";
import { useTimedCarousel } from "@/hooks/useTimedCarousel";
import { htmlToText } from "@/lib/htmlToText";
import { toast } from "sonner";

// Penanda "sudah dibaca" per kampanye untuk sesi login ini (tab). Popup tidak muncul lagi
// saat pindah halaman; kampanye baru tetap ditampilkan karena id-nya berbeda.
function ackStorageKey(userId: string | undefined, campaignId: string) {
  return `vms-hse-ack:${userId ?? "anon"}:${campaignId}`;
}

function isAckedThisSession(userId: string | undefined, campaignId: string): boolean {
  try {
    return window.sessionStorage.getItem(ackStorageKey(userId, campaignId)) === "1";
  } catch {
    return false;
  }
}

function markAckedThisSession(userId: string | undefined, campaignId: string) {
  try {
    window.sessionStorage.setItem(ackStorageKey(userId, campaignId), "1");
  } catch {
    /* penyimpanan tidak tersedia: popup mungkin muncul lagi, tidak fatal */
  }
}

const URL_STALE_MS = 4 * 60 * 1000; // URL bertanda tangan berlaku 5 menit

/**
 * Gerbang popup K3 wajib baca. Dialog baru tampil setelah data dan foto kampanye siap, sehingga
 * waktu baca wajib dihitung sejak pembaca benar-benar melihat materi.
 */
export function HseMandatoryPopupGate() {
  const { me } = useSession();
  const queryClient = useQueryClient();
  // Kampanye yang sedang ditampilkan dikunci di sini: setelah tampil, server tidak lagi mengembalikannya
  // hari ini, tetapi dialog harus tetap terbuka sampai dibaca dan dikonfirmasi.
  const [shown, setShown] = useState<HseCampaign | null>(null);

  // Ambil popup kampanye K3 yang aktif untuk pengguna saat ini
  const { data: fetched, isError } = useQuery<HseCampaign | null>({
    queryKey: ["hse", "active-popup", me?.user_id],
    queryFn: () => (me ? fetchActiveHsePopup() : Promise.resolve(null)),
    enabled: Boolean(me),
    staleTime: 60 * 1000,
  });
  const campaign = shown ?? fetched ?? null;

  const mediaIds = campaign?.media_ids ?? [];
  const mediaQueries = useQueries({
    queries: mediaIds.map((fileId) => ({
      queryKey: ["fileUrl", fileId, "view"],
      queryFn: async () => (await fetchFileUrl(fileId, "view")).url,
      staleTime: URL_STALE_MS,
      retry: 1,
    })),
  });

  useEffect(() => {
    if (isError) toast.error("Gagal memuat panduan keselamatan kerja (K3/HSE).");
  }, [isError]);

  // Kunci kampanye yang baru diterima (pola "simpan dari render sebelumnya", bukan efek).
  if (fetched && !shown && !isAckedThisSession(me?.user_id, fetched.id)) setShown(fetched);

  if (!campaign) return null;
  if (isAckedThisSession(me?.user_id, campaign.id)) return null;
  const mediaLoading = mediaQueries.some((q) => q.isPending);
  if (mediaLoading) return null;

  const slides: CarouselSlide[] = mediaIds.flatMap((_fileId, i) => {
    const src = mediaQueries[i]?.data;
    return src ? [{ src, alt: `${campaign.title} (foto ${i + 1})` }] : [];
  });

  return (
    <HseCampaignPopup
      key={campaign.id}
      campaign={campaign}
      slides={slides}
      onAcknowledged={() => {
        markAckedThisSession(me?.user_id, campaign.id);
        setShown(null);
        queryClient.setQueryData(["hse", "active-popup", me?.user_id], null);
      }}
    />
  );
}

function HseCampaignPopup({
  campaign,
  slides,
  onAcknowledged,
}: {
  campaign: HseCampaign;
  slides: CarouselSlide[];
  onAcknowledged: () => void;
}) {
  // Dialog ini hanya di-mount saat tampil, jadi timer dimulai saat materi terlihat.
  const startedAt = useRef(0);
  const cooldownTotal = campaign.cooldown_seconds || 0;
  const carousel = useTimedCarousel({ count: slides.length, totalSeconds: cooldownTotal });
  const { remaining, done, progress } = carousel;
  const isLegacyImage = slides.length === 0 && Boolean(campaign.media_url);

  useEffect(() => {
    startedAt.current = Date.now();
    // Catat "sudah melihat hari ini" saat materi benar-benar tampil (idempoten di server).
    markHseCampaignSeen(campaign.id).catch(() => undefined);
  }, [campaign.id]);

  const ackMutation = useMutation({
    mutationFn: async () => {
      const readSeconds = Math.max(1, Math.round((Date.now() - startedAt.current) / 1000));
      await acknowledgeHseCampaign(
        campaign.id,
        readSeconds,
        `Web Browser (${navigator.userAgent.slice(0, 80)})`
      );
    },
    onSuccess: () => {
      toast.success("Terima kasih telah membaca panduan keselamatan kerja (K3/HSE).");
      onAcknowledged();
    },
    onError: () => {
      toast.error("Gagal mengonfirmasi pembacaan kampanye. Coba lagi.");
    },
  });

  const isButtonDisabled = !done || ackMutation.isPending;

  return (
    <VmsDialog
      open={true}
      title="PANDUAN KESELAMATAN KERJA (K3 / HSE)"
      size="xl"
      hideClose
      onClose={() => {
        // Non-skippable: dialog tidak bisa ditutup sebelum membaca dan klik konfirmasi
      }}
      onOpenAutoFocus={(e) => {
        // Fokus awal ke dialog (bukan tombol navigasi foto), agar pembaca layar mulai dari judul.
        e.preventDefault();
        (e.currentTarget as HTMLElement | null)?.focus();
      }}
      footer={
        <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <div className="flex items-center gap-1.5 text-xs text-mist">
              {done ? (
                <>
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                  <TextBlock as="span" className="font-medium text-emerald-600">
                    Waktu baca selesai, silakan konfirmasi
                  </TextBlock>
                </>
              ) : (
                <>
                  <Clock className="h-4 w-4 shrink-0 animate-pulse text-amber-500 motion-reduce:animate-none" />
                  <TextBlock as="span" role="timer" className="font-semibold text-amber-600" aria-live="off">
                    Wajib membaca selama {remaining} detik lagi
                  </TextBlock>
                </>
              )}
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-line" aria-hidden>
              <div
                className="h-full rounded-full bg-emerald-500 transition-[width] duration-300 ease-linear motion-reduce:transition-none"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <ActionButton
            variant="default"
            disabled={isButtonDisabled}
            onClick={() => ackMutation.mutate()}
            className="h-11 w-full px-6 font-semibold sm:w-auto sm:shrink-0"
          >
            <TextBlock as="span">
              {ackMutation.isPending
                ? "Menyimpan konfirmasi..."
                : !done
                ? `Baca dulu, tombol aktif dalam ${remaining} detik`
                : "Saya Telah Membaca dan Memahami Panduan Ini"}
            </TextBlock>
          </ActionButton>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3.5">
          <ShieldAlert className="mt-0.5 h-6 w-6 shrink-0 text-amber-600" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <TextBlock as="span" className="rounded-full bg-amber-500/20 px-2.5 py-0.5 text-[11px] font-bold text-amber-700">
                KAMPANYE KESELAMATAN
              </TextBlock>
              {campaign.target_audience !== "ALL" && (
                <TextBlock as="span" className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-semibold text-primary">
                  Sasaran: {campaign.target_audience}
                </TextBlock>
              )}
            </div>
            <TextBlock as="h3" className="mt-1 text-base font-bold leading-snug text-ink">
              {campaign.title}
            </TextBlock>
          </div>
        </div>

        {slides.length > 0 && (
          <CampaignMediaCarousel
            slides={slides}
            index={carousel.index}
            onPrev={carousel.goPrev}
            onNext={carousel.goNext}
            onGoTo={carousel.goTo}
          />
        )}

        {isLegacyImage && (
          <div className="overflow-hidden rounded-xl border border-line bg-surface-elevated">
            <ImageView
              src={campaign.media_url ?? ""}
              alt={campaign.title}
              className="h-[45vh] w-full object-contain md:h-[50vh]"
            />
          </div>
        )}

        <div className="whitespace-pre-line rounded-xl border border-line/60 bg-surface-elevated/60 p-4 text-sm leading-relaxed text-ink">
          {htmlToText(campaign.content_body)}
        </div>

        <div className="flex items-start gap-2.5 rounded-xl border border-primary/20 bg-primary/5 p-3.5 text-xs text-mist">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <TextBlock as="p">
            Demi keselamatan kerja seluruh tim Visiontech di kantor maupun di lokasi proyek lapangan,
            setiap anggota wajib membaca dan mematuhi panduan K3 ini sebelum melanjutkan pekerjaan di sistem.
          </TextBlock>
        </div>
      </div>
    </VmsDialog>
  );
}
