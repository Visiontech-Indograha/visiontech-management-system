import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FaceEnrollCapture } from "@/components/organisms/face/FaceEnrollCapture";
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

  it("pendaftaran: empat pose dijepret lalu diunggah sekali (tanpa tantangan liveness)", async () => {
    stubCamera();
    const calls = mockApi((c) => (c.url === "/face/enroll" ? { data: { enrolled: true, images_used: 4 } } : undefined));
    const onEnrolled = vi.fn();
    render(<FaceEnrollCapture onEnrolled={onEnrolled} />);
    fireEvent.click(screen.getByRole("button", { name: "Mulai Pendaftaran Wajah" }));

    await advance(8000); // 4 pose × 1,6 dtk
    await waitFor(() => expect(onEnrolled).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Wajah berhasil didaftarkan.")).toBeInTheDocument();
    expect(stopTrack).toHaveBeenCalled(); // kamera dimatikan setelah selesai
    expect(calls.map((c) => c.url)).toEqual(["/face/enroll"]);
    const enroll = calls[0]!.data as Record<string, unknown>;
    expect(enroll.files).toHaveLength(4);
    expect(enroll.liveness).toBeUndefined();
  });

  it("galat server pendaftaran ditampilkan dan bisa dicoba lagi", async () => {
    stubCamera();
    mockApi((c) =>
      c.url === "/face/enroll" ? apiError(409, "FACE_DUPLICATE", "Wajah ini sudah terdaftar untuk karyawan lain.") : undefined,
    );
    const onEnrolled = vi.fn();
    render(<FaceEnrollCapture onEnrolled={onEnrolled} />);
    fireEvent.click(screen.getByRole("button", { name: "Mulai Pendaftaran Wajah" }));
    await advance(8000);
    expect(await screen.findByRole("alert")).toHaveTextContent("sudah terdaftar untuk karyawan lain");
    expect(onEnrolled).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Coba Lagi" })).toBeInTheDocument();
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
});
