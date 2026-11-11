import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, fireEvent, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  slideIntervalMs,
  remainingSeconds,
  nextSlideIndex,
  prevSlideIndex,
  carouselConfigError,
} from "@/lib/hseCarousel";
import { useTimedCarousel } from "@/hooks/useTimedCarousel";
import { CampaignMediaCarousel } from "@/components/organisms/hse/CampaignMediaCarousel";
import { HseMandatoryPopupGate } from "@/components/organisms/hse/HseMandatoryPopupGate";
import { fetchActiveHsePopup, type HseCampaign } from "@/services/hseService";

vi.mock("@/services/hseService", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/services/hseService")>();
  return {
    ...actual,
    fetchActiveHsePopup: vi.fn(),
    acknowledgeHseCampaign: vi.fn(() => Promise.resolve()),
  };
});

vi.mock("@/stores/sessionStore", () => ({
  useSession: () => ({ me: { user_id: "user-uji" } }),
}));

/**
 * Majukan waktu palsu per 250 dtk, masing-masing dalam `act` sendiri, seperti waktu nyata:
 * setiap pergantian foto memicu render lalu penjadwalan timer berikutnya.
 */
function advance(ms: number) {
  for (let elapsed = 0; elapsed < ms; elapsed += 250) {
    act(() => {
      vi.advanceTimersByTime(250);
    });
  }
}

function stubReducedMotion(matches: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: matches && query.includes("reduce"),
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    })),
  );
}

describe("logika carousel K3 (murni)", () => {
  it("interval = durasi / jumlah foto (50 dtk / 5 foto = 10 dtk)", () => {
    expect(slideIntervalMs(50, 5)).toBe(10_000);
    expect(slideIntervalMs(30, 4)).toBe(7_500);
  });

  it("sisa detik dibulatkan ke atas dan tidak pernah negatif", () => {
    expect(remainingSeconds(50, 0)).toBe(50);
    expect(remainingSeconds(50, 49_100)).toBe(1);
    expect(remainingSeconds(50, 50_000)).toBe(0);
    expect(remainingSeconds(50, 99_000)).toBe(0);
  });

  it("indeks berputar di kedua arah", () => {
    expect(nextSlideIndex(4, 5)).toBe(0);
    expect(prevSlideIndex(0, 5)).toBe(4);
    expect(nextSlideIndex(0, 0)).toBe(0);
  });

  it("validasi durasi dan jumlah foto mengikuti aturan API", () => {
    expect(carouselConfigError(5, 50)).toBeNull();
    expect(carouselConfigError(0, 5)).toBeNull(); // kampanye tanpa foto: aturan lama
    expect(carouselConfigError(5, 5)).not.toBeNull(); // di bawah 10 dtk
    expect(carouselConfigError(5, 301)).not.toBeNull(); // di atas 300 dtk
    expect(carouselConfigError(9, 300)).not.toBeNull(); // lebih dari 8 foto
    expect(carouselConfigError(4, 11)).not.toBeNull(); // 4 foto butuh minimal 12 dtk
    expect(carouselConfigError(4, 12)).toBeNull();
  });
});

describe("useTimedCarousel (fake timers)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    stubReducedMotion(false);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("geser otomatis tiap 10 dtk dan selesai tepat di 50 dtk", () => {
    const { result } = renderHook(() => useTimedCarousel({ count: 5, totalSeconds: 50 }));
    expect(result.current.index).toBe(0);
    expect(result.current.remaining).toBe(50);

    advance(10_000);
    expect(result.current.index).toBe(1);
    advance(10_000);
    expect(result.current.index).toBe(2);
    advance(19_000);
    expect(result.current.index).toBe(3);
    expect(result.current.done).toBe(false);

    advance(2_000); // t = 41 dtk
    expect(result.current.index).toBe(4);
    expect(result.current.remaining).toBe(9);

    advance(9_000); // t = 50 dtk: waktu wajib baca habis
    expect(result.current.remaining).toBe(0);
    expect(result.current.done).toBe(true);
    expect(result.current.progress).toBe(100);

    advance(1_000); // geser berputar ke foto pertama
    expect(result.current.index).toBe(0);
  });

  it("navigasi manual tidak mempercepat timer total, dan interval dihitung ulang dari pindah terakhir", () => {
    const { result } = renderHook(() => useTimedCarousel({ count: 5, totalSeconds: 50 }));

    advance(4_000);
    act(() => result.current.goNext()); // manual ke foto 2 pada t=4 dtk
    expect(result.current.index).toBe(1);

    // Belum 10 dtk sejak pindah manual: tidak boleh langsung loncat.
    advance(9_000);
    expect(result.current.index).toBe(1);
    advance(1_000);
    expect(result.current.index).toBe(2);

    // Timer total tetap berjalan dari awal (t = 14 dtk tersisa 36 dtk).
    expect(result.current.remaining).toBe(36);
    advance(36_000);
    expect(result.current.done).toBe(true);
  });

  it("panah kiri/kanan keyboard pindah foto", () => {
    const { result } = renderHook(() => useTimedCarousel({ count: 3, totalSeconds: 30 }));
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
    });
    expect(result.current.index).toBe(1);
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" }));
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" }));
    });
    expect(result.current.index).toBe(2);
  });

  it("prefers-reduced-motion: tanpa geser otomatis, timer total tetap jalan", () => {
    stubReducedMotion(true);
    const { result } = renderHook(() => useTimedCarousel({ count: 5, totalSeconds: 50 }));
    advance(30_000);
    expect(result.current.index).toBe(0);
    expect(result.current.remaining).toBe(20);
    act(() => result.current.goNext());
    expect(result.current.index).toBe(1);
  });
});

describe("CampaignMediaCarousel", () => {
  const slides = [1, 2, 3, 4, 5].map((n) => ({ src: `/foto-${n}.png`, alt: `Foto ${n}` }));

  it("menampilkan penghitung, titik indikator, dan panah yang memanggil callback", () => {
    const onNext = vi.fn();
    const onPrev = vi.fn();
    const onGoTo = vi.fn();
    render(
      <CampaignMediaCarousel slides={slides} index={1} onPrev={onPrev} onNext={onNext} onGoTo={onGoTo} />,
    );
    expect(screen.getByText("2 dari 5")).toBeInTheDocument();
    expect(screen.getByText("2 dari 5")).toHaveAttribute("aria-live", "polite");
    expect(screen.getAllByRole("button", { name: /Tampilkan foto/ })).toHaveLength(5);
    expect(screen.getByRole("button", { name: /Tampilkan foto 2 dari 5/ })).toHaveAttribute("aria-current", "true");

    fireEvent.click(screen.getByRole("button", { name: "Foto berikutnya" }));
    fireEvent.click(screen.getByRole("button", { name: "Foto sebelumnya" }));
    fireEvent.click(screen.getByRole("button", { name: "Tampilkan foto 4 dari 5" }));
    expect(onNext).toHaveBeenCalledTimes(1);
    expect(onPrev).toHaveBeenCalledTimes(1);
    expect(onGoTo).toHaveBeenCalledWith(3);
  });

  it("geser sentuh ke kiri memanggil foto berikutnya", () => {
    const onNext = vi.fn();
    const onPrev = vi.fn();
    render(
      <CampaignMediaCarousel slides={slides} index={0} onPrev={onPrev} onNext={onNext} onGoTo={() => undefined} />,
    );
    const region = screen.getByRole("region", { name: "Foto panduan K3" });
    fireEvent.touchStart(region, { touches: [{ clientX: 200 }] });
    fireEvent.touchEnd(region, { changedTouches: [{ clientX: 120 }] });
    expect(onNext).toHaveBeenCalledTimes(1);
    expect(onPrev).not.toHaveBeenCalled();
  });
});

describe("HseMandatoryPopupGate: tombol konfirmasi terkunci sampai waktu habis", () => {
  const campaign: HseCampaign = {
    id: "campaign-uji",
    title: "Panduan K3 uji",
    content_body: "Materi keselamatan.",
    target_audience: "ALL",
    media_ids: [],
    media_captions: [],
    media_url: null,
    start_date: "2026-11-01",
    end_date: "2026-11-30",
    is_mandatory: true,
    cooldown_seconds: 50,
    is_active: true,
    created_at: "2026-11-01T00:00:00Z",
  };

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    stubReducedMotion(false);
    vi.mocked(fetchActiveHsePopup).mockResolvedValue(campaign);
    sessionStorage.clear();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("tombol nonaktif dan tanpa tombol tutup sampai 50 dtk, lalu aktif", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <HseMandatoryPopupGate />
      </QueryClientProvider>,
    );

    const button = (await screen.findByText(/Baca dulu, tombol aktif dalam \d+ detik/)).closest("button");
    expect(button).toBeDisabled();
    expect(screen.queryByRole("button", { name: /close/i })).not.toBeInTheDocument();

    advance(49_000);
    expect(screen.getByText(/tombol aktif dalam 1 detik/).closest("button")).toBeDisabled();

    advance(1_500);
    const confirm = (await screen.findByText("Saya Telah Membaca dan Memahami Panduan Ini")).closest("button");
    expect(confirm).toBeEnabled();
  });
});
