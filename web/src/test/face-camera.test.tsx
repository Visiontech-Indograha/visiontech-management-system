import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FaceEnrollCapture } from "@/components/organisms/face/FaceEnrollCapture";
import { FaceProbeDialog } from "@/components/organisms/face/FaceProbeDialog";
import { apiError, mockApi } from "./utils";

const toast = vi.hoisted(() => ({ warning: vi.fn(), success: vi.fn(), error: vi.fn() }));
vi.mock("sonner", () => ({ toast }));

const stopTrack = vi.fn();

/** jsdom tidak punya kamera/kanvas: tiru getUserMedia, video 640×480, dan kanvas yang menghasilkan Blob. */
function stubCamera(opts: { getUserMedia?: () => Promise<unknown>; secure?: boolean } = {}) {
  Object.defineProperty(window, "isSecureContext", { value: opts.secure ?? true, configurable: true });
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: opts.getUserMedia ?? (async () => ({ getTracks: () => [{ stop: stopTrack }] })) },
  });
  Object.defineProperty(HTMLVideoElement.prototype, "videoWidth", { get: () => 640, configurable: true });
  Object.defineProperty(HTMLVideoElement.prototype, "videoHeight", { get: () => 480, configurable: true });
  HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({ drawImage: vi.fn() })) as never;
  HTMLCanvasElement.prototype.toBlob = function (cb: BlobCallback) {
    cb(new Blob(["jpeg"], { type: "image/jpeg" }));
  };
}

const domEx = (name: string) => () => Promise.reject(new DOMException("x", name));
const advance = (ms: number) =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });

describe("Kamera wajah di web", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    stopTrack.mockClear();
    toast.warning.mockClear();
  });
  afterEach(() => vi.useRealTimers());

  it("pendaftaran: dua tantangan dibuktikan server, lalu pose, lalu unggah dengan liveness bukti", async () => {
    stubCamera();
    let n = 0;
    const calls = mockApi((c) => {
      if (c.url === "/face/challenge-check") {
        n += 1;
        const challenge = (c.data as Record<string, string>).challenge;
        return {
          data:
            challenge === "depan"
              ? { status: "sukses", detail: "ok", proof: null }
              : { status: "sukses", detail: "ok", proof: `bukti-${n}` },
        };
      }
      if (c.url === "/face/enroll") return { data: { enrolled: 4 } };
    });
    const onEnrolled = vi.fn();
    render(<FaceEnrollCapture onEnrolled={onEnrolled} />);
    fireEvent.click(screen.getByRole("button", { name: "Mulai Pendaftaran Wajah" }));

    await advance(8000); // 4 pose × 1,6 dtk
    await waitFor(() => expect(onEnrolled).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Wajah berhasil didaftarkan.")).toBeInTheDocument();
    expect(stopTrack).toHaveBeenCalled(); // kamera dimatikan setelah selesai

    const checks = calls
      .filter((c) => c.url === "/face/challenge-check")
      .map((c) => (c.data as Record<string, string>).challenge);
    expect(checks).toHaveLength(3); // 2 tantangan + 1 langkah meluruskan
    expect(checks[2]).toBe("depan");
    expect(new Set(checks.slice(0, 2)).size).toBe(2); // dua tantangan BERBEDA
    expect(["kiri", "kanan", "atas", "bawah", "buka_mulut"]).toEqual(expect.arrayContaining(checks.slice(0, 2)));

    const enroll = calls.find((c) => c.url === "/face/enroll")!.data as Record<string, unknown>;
    expect(enroll.files).toHaveLength(4);
    const liveness = JSON.parse(enroll.liveness as string);
    expect(liveness.passed).toBe(true);
    expect(liveness.proofs).toHaveLength(2); // bukti "depan" TIDAK ikut
    expect(liveness.challenges).toEqual(checks.slice(0, 2));
  });

  it("menampilkan petunjuk server saat gerakan belum cukup", async () => {
    stubCamera();
    let call = 0;
    mockApi((c) => {
      if (c.url !== "/face/challenge-check") return undefined;
      call += 1;
      return call === 1
        ? { data: { status: "menunggu", detail: "Tengok lagi ke KIRI sedikit.", proof: null } }
        : { data: { status: "sukses", detail: "ok", proof: `b${call}` } };
    });
    render(<FaceProbeDialog title="Verifikasi" onCancel={() => undefined} onDone={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: "Mulai Verifikasi Wajah" }));
    await waitFor(() => expect(screen.getByTestId("face-hint")).toHaveTextContent("Tengok lagi ke KIRI sedikit."));
  });

  it.each([
    ["NotAllowedError", /ikon gembok/],
    ["SecurityError", /ikon gembok/],
    ["NotFoundError", /tidak ditemukan/],
    ["NotReadableError", /sedang dipakai aplikasi lain/],
  ])("galat kamera %s → pesan yang menunjukkan jalan keluar", async (name, message) => {
    stubCamera({ getUserMedia: domEx(name) });
    mockApi(() => undefined);
    render(<FaceEnrollCapture onEnrolled={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: "Mulai Pendaftaran Wajah" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("button", { name: "Coba Lagi" })).toBeInTheDocument();
  });

  it("bukan HTTPS: pesan jelas tanpa memanggil kamera", async () => {
    const getUserMedia = vi.fn();
    stubCamera({ getUserMedia, secure: false });
    render(<FaceEnrollCapture onEnrolled={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: "Mulai Pendaftaran Wajah" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("HTTPS");
    expect(getUserMedia).not.toHaveBeenCalled();
  });

  it("verifikasi absen: probe terunggah → onDone(probe_id)", async () => {
    stubCamera();
    const calls = mockApi((c) => {
      if (c.url === "/face/challenge-check") return { data: { status: "sukses", detail: "ok", proof: "p" } };
      if (c.url === "/face/probe") return { data: { probe_id: "probe-123" } };
    });
    const onDone = vi.fn();
    render(<FaceProbeDialog title="Verifikasi" onCancel={() => undefined} onDone={onDone} />);
    fireEvent.click(screen.getByRole("button", { name: "Mulai Verifikasi Wajah" }));
    await advance(2000);
    await waitFor(() => expect(onDone).toHaveBeenCalledWith("probe-123"));
    const probe = calls.find((c) => c.url === "/face/probe")!.data as Record<string, unknown>;
    expect(probe.file).toBeInstanceOf(Blob);
    expect(JSON.parse(probe.liveness as string).passed).toBe(true);
  });

  it("face-service mati (503): absen tetap lanjut tanpa probe dan pengguna diberi tahu", async () => {
    stubCamera();
    mockApi((c) => {
      if (c.url === "/face/challenge-check") return { data: { status: "sukses", detail: "ok", proof: "p" } };
      if (c.url === "/face/probe") return apiError(503, "FACE_SERVICE_UNAVAILABLE", "Layanan wajah tidak tersedia.");
    });
    const onDone = vi.fn();
    render(<FaceProbeDialog title="Verifikasi" onCancel={() => undefined} onDone={onDone} />);
    fireEvent.click(screen.getByRole("button", { name: "Mulai Verifikasi Wajah" }));
    await advance(2000);
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(null));
    expect(toast.warning).toHaveBeenCalled();
  });

  it("galat server selain 503 ditampilkan dan bisa dicoba lagi", async () => {
    stubCamera();
    mockApi((c) => {
      if (c.url === "/face/challenge-check") return { data: { status: "sukses", detail: "ok", proof: "p" } };
      if (c.url === "/face/probe") return apiError(422, "FACE_NOT_DETECTED", "Wajah tidak terdeteksi pada gambar.");
    });
    const onDone = vi.fn();
    render(<FaceProbeDialog title="Verifikasi" onCancel={() => undefined} onDone={onDone} />);
    fireEvent.click(screen.getByRole("button", { name: "Mulai Verifikasi Wajah" }));
    await advance(2000);
    expect(await screen.findByRole("alert")).toHaveTextContent("Wajah tidak terdeteksi");
    expect(onDone).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Coba Lagi" })).toBeInTheDocument();
  });
});
