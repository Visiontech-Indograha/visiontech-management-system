import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/stores/sessionStore";
import {
  fetchActiveHsePopup,
  acknowledgeHseCampaign,
  type HseCampaign,
} from "@/services/hseService";
import { fetchFileUrl } from "@/services/fileService";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ImageView } from "@/components/molecules/ImageView";
import { TextBlock } from "@/components/molecules/TextBlock";
import { CampaignMediaCarousel, type CarouselSlide } from "./CampaignMediaCarousel";
import { ShieldAlert, Clock, CheckCircle2, Maximize, Minimize } from "@/components/molecules/Glyphs";
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
 * waktu baca wajib dihitung sejak pembaca benar-benar melihat materi. Reload sebelum konfirmasi
 * memunculkan popup lagi dengan timer dari awal (tidak ada penanda "sudah tampil").
 */
export function HseMandatoryPopupGate() {
  const { me } = useSession();
  const queryClient = useQueryClient();
  // Kampanye yang sedang ditampilkan dikunci di sini agar dialog tidak hilang saat data diperbarui
  // (mis. refetch saat fokus jendela). Dialog hanya selesai setelah konfirmasi berhasil.
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
    const caption = campaign.media_captions?.[i]?.trim() || undefined;
    return src ? [{ src, alt: `${campaign.title} (foto ${i + 1})`, caption }] : [];
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

/** Ukuran foto asli (rasio lebar/tinggi) per sumber, untuk banner "putar HP" pada layar potret. */
function useAspects(srcs: string[]): Record<string, number> {
  const [aspects, setAspects] = useState<Record<string, number>>({});
  const key = srcs.join("|");
  useEffect(() => {
    let cancelled = false;
    for (const src of key ? key.split("|") : []) {
      const img = new Image();
      img.onload = () => {
        if (!cancelled && img.naturalHeight > 0) {
          setAspects((prev) => ({ ...prev, [src]: img.naturalWidth / img.naturalHeight }));
        }
      };
      img.src = src;
    }
    return () => {
      cancelled = true;
    };
  }, [key]);
  return aspects;
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
  const rootRef = useRef<HTMLDivElement>(null);
  const cooldownTotal = campaign.cooldown_seconds || 0;
  const carousel = useTimedCarousel({ count: slides.length, totalSeconds: cooldownTotal });
  const { remaining, done, progress } = carousel;
  const isLegacyImage = slides.length === 0 && Boolean(campaign.media_url);
  const aspects = useAspects(slides.map((s) => s.src));
  const [sheetOpen, setSheetOpen] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    startedAt.current = Date.now();
  }, [campaign.id]);

  useEffect(() => {
    const onChange = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

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

  const toggleFullscreen = () => {
    if (document.fullscreenElement) {
      void document.exitFullscreen?.();
      return;
    }
    const el = rootRef.current;
    if (!el?.requestFullscreen) return;
    el.requestFullscreen().then(() => {
      // Kunci orientasi lanskap bila didukung; galat diabaikan (tidak semua peramban mendukung).
      const orientation = screen.orientation as ScreenOrientation & { lock?: (o: string) => Promise<void> };
      orientation?.lock?.("landscape").catch(() => undefined);
    }).catch(() => undefined);
  };

  const currentSrc = slides[Math.min(carousel.index, slides.length - 1)]?.src;
  const currentAspect = currentSrc ? aspects[currentSrc] : undefined;
  const portraitScreen =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(orientation: portrait)").matches;
  const showRotateHint = portraitScreen && currentAspect !== undefined && currentAspect > 1.2;

  const readBar = (
    <div className="flex flex-col gap-1.5">
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
  );

  const confirmButton = (
    <ActionButton
      variant="default"
      disabled={isButtonDisabled}
      onClick={() => ackMutation.mutate()}
      className="h-11 w-full px-6 font-semibold"
    >
      <TextBlock as="span">
        {ackMutation.isPending
          ? "Menyimpan konfirmasi..."
          : !done
          ? `Baca dulu, tombol aktif dalam ${remaining} detik`
          : "Saya Telah Membaca dan Memahami Panduan Ini"}
      </TextBlock>
    </ActionButton>
  );

  const textContent = (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <TextBlock as="span" className="rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-bold text-amber-700">
          KAMPANYE KESELAMATAN
        </TextBlock>
        {campaign.target_audience !== "ALL" && (
          <TextBlock as="span" className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
            Sasaran: {campaign.target_audience}
          </TextBlock>
        )}
      </div>
      <TextBlock as="h3" className="text-lg leading-snug font-bold text-ink">
        {campaign.title}
      </TextBlock>
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
  );

  return (
    <VmsDialog
      open={true}
      title="PANDUAN KESELAMATAN KERJA (K3 / HSE)"
      fullscreen
      hideClose
      onClose={() => {
        // Non-skippable: dialog tidak bisa ditutup sebelum membaca dan klik konfirmasi
      }}
      onOpenAutoFocus={(e) => {
        // Fokus awal ke dialog (bukan tombol navigasi foto), agar pembaca layar mulai dari judul.
        e.preventDefault();
        (e.currentTarget as HTMLElement | null)?.focus();
      }}
    >
      <div ref={rootRef} className="relative flex min-h-0 flex-1 flex-col bg-background lg:flex-row">
        {/* Foto: layar penuh di ponsel; di layar lebar ~68% lebar. Tinggi area foto tetap antar slide. */}
        <div className="relative flex min-h-0 flex-1 flex-col p-2 sm:p-3 lg:w-[70%] lg:p-4">
          {slides.length > 0 ? (
            <CampaignMediaCarousel
              fill
              slides={slides}
              index={carousel.index}
              onPrev={carousel.goPrev}
              onNext={carousel.goNext}
              onGoTo={carousel.goTo}
              onInteract={carousel.holdAutoAdvance}
            />
          ) : isLegacyImage ? (
            <div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden rounded-xl border border-line bg-surface-elevated">
              <ImageView src={campaign.media_url ?? ""} alt={campaign.title} className="h-full w-full object-contain" />
            </div>
          ) : null}

          <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5">
            <ActionButton
              variant="secondary"
              size="sm"
              aria-label={fullscreen ? "Keluar layar penuh" : "Layar penuh"}
              onClick={toggleFullscreen}
              className="bg-black/55 text-white hover:bg-black/70"
            >
              {fullscreen ? <Minimize /> : <Maximize />}
              <TextBlock as="span" className="hidden sm:inline">
                {fullscreen ? "Keluar layar penuh" : "Layar penuh"}
              </TextBlock>
            </ActionButton>
            <ActionButton
              variant="secondary"
              size="sm"
              className="bg-black/55 text-white hover:bg-black/70 lg:hidden"
              aria-expanded={sheetOpen}
              onClick={() => setSheetOpen((v) => !v)}
            >
              {sheetOpen ? "Tutup keterangan" : "Baca keterangan"}
            </ActionButton>
          </div>

          {showRotateHint && (
            <div
              role="status"
              className="absolute top-14 right-3 left-3 z-10 rounded-lg bg-amber-500/90 px-3 py-2 text-center text-xs font-semibold text-black lg:hidden"
            >
              <TextBlock as="span">Putar HP agar foto lebih besar</TextBlock>
            </div>
          )}
        </div>

        {/* Teks: panel kanan di layar lebar; bottom-sheet tertutup di ponsel (dibuka dari tombol). */}
        {/*
          Satu panel untuk teks dan bilah baca (tombol konfirmasi hanya ada sekali di DOM).
          Ponsel: melayang di bawah foto; teks tersembunyi sampai "Baca keterangan" dibuka (bottom-sheet).
          Layar lebar: kolom kanan tetap.
        */}
        <div
          className={
            "flex min-h-0 flex-col border-line lg:static lg:w-[30%] lg:flex-1 lg:border-l lg:bg-background " +
            (sheetOpen
              ? "absolute inset-x-0 bottom-0 z-20 max-h-[70%] rounded-t-2xl border-t bg-background shadow-2xl"
              : "absolute inset-x-0 bottom-0 z-10 p-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]")
          }
        >
          <div className={sheetOpen ? "min-h-0 flex-1 overflow-y-auto p-4" : "hidden lg:block lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:p-5"}>
            {textContent}
          </div>
          <div
            className={
              "shrink-0 space-y-2 p-3 backdrop-blur sm:p-4 lg:space-y-3 lg:rounded-none lg:border-t lg:border-line lg:bg-background lg:shadow-none " +
              (sheetOpen ? "border-t border-line bg-background/95" : "rounded-xl bg-background/85 shadow-lg")
            }
          >
            {readBar}
            {confirmButton}
          </div>
        </div>
      </div>
    </VmsDialog>
  );
}
