import { beforeEach, describe, expect, it, vi } from "vitest";

type Opsi = { params: { page: number; size: number } };
const calls: Opsi[] = [];
let handler: (o: Opsi) => { data: unknown[]; headers: Record<string, string> } = () => ({ data: [], headers: {} });
vi.mock("@/lib/apiClient", () => ({
  api: {
    get: async (_url: string, o: Opsi) => {
      calls.push(o);
      if (o.params.size > 100) throw new Error("422");
      return handler(o);
    },
  },
}));

import { BATAS_UKURAN_HALAMAN, ambilSemuaHalaman } from "@/services/hikvisionService";

const baris = (n: number) => Array.from({ length: n }, (_, i) => ({ id: String(i) }));

describe("ambilSemuaHalaman", () => {
  beforeEach(() => {
    calls.length = 0;
  });

  it("tidak pernah meminta size di atas batas API (kalau tidak, 422)", async () => {
    handler = (o) => ({ data: o.params.page === 1 ? baris(100) : baris(30), headers: { "x-total-count": "130" } });
    const hasil = await ambilSemuaHalaman("/hikvision/devices");
    expect(hasil).toHaveLength(130);
    expect(calls.length).toBeGreaterThan(1);
    for (const o of calls) expect(o.params.size).toBeLessThanOrEqual(BATAS_UKURAN_HALAMAN);
  });

  it("berhenti setelah satu halaman bila datanya sedikit", async () => {
    handler = () => ({ data: baris(3), headers: {} });
    expect(await ambilSemuaHalaman("/x")).toHaveLength(3);
    expect(calls).toHaveLength(1);
  });
});
