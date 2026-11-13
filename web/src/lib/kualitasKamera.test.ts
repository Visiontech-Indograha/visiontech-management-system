import { describe, expect, it } from "vitest";
import {
  accuracyText,
  brightnessHint,
  captureBest,
  faceHint,
  pickBestIndex,
  scoreImageData,
} from "./kualitasKamera";

const flat = (v: number, w = 8, h = 8) => new Uint8ClampedArray(w * h * 4).fill(v);

describe("kualitasKamera", () => {
  it("mengukur kecerahan rata-rata", () => {
    expect(scoreImageData(flat(0), 8, 8).brightness).toBe(0);
    expect(scoreImageData(flat(255), 8, 8).brightness).toBeCloseTo(255, 0);
  });
  it("petunjuk gelap/silau/baik", () => {
    expect(brightnessHint(30)).toMatch(/gelap/);
    expect(brightnessHint(240)).toMatch(/silau/);
    expect(brightnessHint(120)).toBeNull();
  });
  it("petunjuk wajah: tidak ada, kecil, miring, lewati bila tanpa FaceDetector", () => {
    expect(faceHint(undefined, 640, 480)).toBeNull();
    expect(faceHint([], 640, 480)).toMatch(/Hadapkan wajah/);
    expect(faceHint([{ width: 40, height: 40 }], 640, 480)).toMatch(/Dekatkan/);
    const tilted = { width: 300, height: 300, eyes: [{ x: 100, y: 100 }, { x: 200, y: 180 }] };
    expect(faceHint([tilted], 640, 480)).toMatch(/miring/);
    expect(faceHint([{ ...tilted, eyes: [{ x: 100, y: 100 }, { x: 200, y: 105 }] }], 640, 480)).toBeNull();
  });
  it("memilih bingkai paling tajam dan terang", () => {
    const i = pickBestIndex([
      { brightness: 20, sharpness: 30 },
      { brightness: 125, sharpness: 25 },
      { brightness: 125, sharpness: 5 },
    ]);
    expect(i).toBe(1);
  });
  it("captureBest memakai jam suntikan, melewati bingkai gagal", async () => {
    const waits: number[] = [];
    let n = 0;
    const best = await captureBest(
      () => {
        n++;
        return n === 2 ? null : { frame: n, score: { brightness: 125, sharpness: n === 3 ? 50 : 10 } };
      },
      async (ms) => void waits.push(ms),
      4,
      250,
    );
    expect(best).toBe(3);
    expect(waits).toEqual([250, 250, 250]);
    expect(await captureBest(() => null, async () => undefined)).toBeNull();
  });
  it("teks akurasi dan catatan bila kasar", () => {
    expect(accuracyText(undefined)).toBeNull();
    expect(accuracyText(25)).toEqual({ label: "Akurasi lokasi ±25 m", note: null });
    expect(accuracyText(250.4)?.note).toMatch(/laptop/);
  });
});
