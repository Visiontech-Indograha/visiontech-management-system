import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act, renderHook } from "@testing-library/react";
import {
  clampScale,
  clampPan,
  zoomAround,
  doubleTapZoom,
  wheelScale,
  ZOOM_MAX,
  ZOOM_RESET,
} from "@/lib/zoomPan";
import { lowResolutionWarning, mixedOrientationNote, orientationOf } from "@/lib/mediaQuality";
import { useTimedCarousel } from "@/hooks/useTimedCarousel";
import { ZoomableImage } from "@/components/molecules/ZoomableImage";

const VIEW = { width: 400, height: 300 };

describe("zoom dan geser (murni)", () => {
  it("skala dibatasi 1x sampai 4x", () => {
    expect(clampScale(10)).toBe(ZOOM_MAX);
    expect(clampScale(0.2)).toBe(1);
    expect(clampScale(Number.NaN)).toBe(1);
  });

  it("geser tidak melewati tepi gambar yang diperbesar", () => {
    const panned = clampPan({ scale: 2, x: 9999, y: -9999 }, VIEW);
    expect(panned.x).toBe(200); // (400*2-400)/2
    expect(panned.y).toBe(-150); // (300*2-300)/2
    expect(clampPan({ scale: 1, x: 50, y: 50 }, VIEW)).toEqual({ scale: 1, x: 0, y: 0 });
  });

  it("zoom menjaga titik di bawah kursor tetap di tempatnya", () => {
    const anchor = { x: 100, y: 50 };
    const next = zoomAround(ZOOM_RESET, 2, anchor, VIEW);
    // Titik (100, 50) pada gambar 1x berada di (100, 50) pada gambar 2x setelah pergeseran.
    expect(next.scale).toBe(2);
    // x = 100 - (100 - 0) * 2 = -100; y = 50 - (50 - 0) * 2 = -50 (keduanya di dalam batas geser).
    expect(next.x).toBeCloseTo(-100, 5);
    expect(next.y).toBeCloseTo(-50, 5);
  });

  it("ketuk dua kali: 1x ke 2x lalu kembali ke 1x", () => {
    const zoomed = doubleTapZoom(ZOOM_RESET, { x: 0, y: 0 }, VIEW);
    expect(zoomed.scale).toBe(2);
    const back = doubleTapZoom(zoomed, { x: 0, y: 0 }, VIEW);
    expect(back).toEqual({ scale: 1, x: 0, y: 0 });
  });

  it("roda ke atas memperbesar, ke bawah memperkecil", () => {
    expect(wheelScale(1, -120)).toBeGreaterThan(1);
    expect(wheelScale(2, 120)).toBeLessThan(2);
    expect(wheelScale(4, -500)).toBe(ZOOM_MAX);
  });
});

describe("kualitas foto (murni)", () => {
  it("peringatan resolusi bila sisi terpendek di bawah 1000 px", () => {
    expect(lowResolutionWarning({ width: 900, height: 1400 })).toMatch(/Resolusi rendah/);
    expect(lowResolutionWarning({ width: 1600, height: 900 })).toMatch(/Resolusi rendah/);
    expect(lowResolutionWarning({ width: 1600, height: 1100 })).toBeNull();
  });

  it("ringkasan campuran potret dan lanskap", () => {
    expect(orientationOf({ width: 900, height: 1400 })).toBe("portrait");
    expect(mixedOrientationNote([{ width: 900, height: 1400 }, { width: 1600, height: 900 }])).toMatch(/Campuran/);
    expect(mixedOrientationNote([{ width: 1600, height: 900 }, { width: 1920, height: 1080 }])).toBeNull();
  });
});

describe("geser otomatis ditunda saat zoom/geser", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("matchMedia", undefined);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  function advance(ms: number) {
    for (let t = 0; t < ms; t += 250) act(() => vi.advanceTimersByTime(250));
  }

  it("interaksi 3 dtk sebelum geser menunda geser hingga 5 dtk sejak interaksi", () => {
    const { result } = renderHook(() => useTimedCarousel({ count: 5, totalSeconds: 50 }));
    advance(7_000);
    act(() => result.current.holdAutoAdvance()); // t = 7 dtk
    advance(3_000); // t = 10 dtk: geser normal akan terjadi, tetapi ditunda
    expect(result.current.index).toBe(0);
    advance(2_000); // t = 12 dtk: 5 dtk sejak interaksi
    expect(result.current.index).toBe(1);
    expect(result.current.remaining).toBe(38);
  });

  it("tidak menunda geser bila sisa waktu wajib baca sudah kurang dari 5 dtk", () => {
    const { result } = renderHook(() => useTimedCarousel({ count: 5, totalSeconds: 50 }));
    advance(46_000);
    act(() => result.current.holdAutoAdvance()); // t = 46 dtk, sisa 4 dtk
    // Geser tiap 10 dtk: t=40 ke foto 5 (index 4); t=50 kembali ke index 0 tanpa menunggu jeda zoom.
    advance(4_000);
    expect(result.current.index).toBe(0);
  });
});

describe("ZoomableImage", () => {
  it("roda mouse memperbesar dan tombol Pas layar mengembalikan 100%", () => {
    const onInteract = vi.fn();
    render(<ZoomableImage src="/foto.png" alt="Foto uji" onInteract={onInteract} />);
    expect(screen.getByText("100%")).toBeInTheDocument();

    const img = screen.getByRole("img", { name: "Foto uji" });
    fireEvent.wheel(img.parentElement as HTMLElement, { deltaY: -200, clientX: 10, clientY: 10 });
    expect(screen.getByText(/^(1\d\d|2\d\d|3\d\d|400)%$/)).toBeInTheDocument();
    expect(onInteract).toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Pas layar" }));
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("tombol Perbesar menaikkan skala dan tidak melewati 400%", () => {
    render(<ZoomableImage src="/foto.png" alt="Foto uji" />);
    const plus = screen.getByRole("button", { name: "Perbesar" });
    for (let i = 0; i < 10; i += 1) fireEvent.click(plus);
    expect(screen.getByText("400%")).toBeInTheDocument();
    expect(plus).toBeDisabled();
  });
});
