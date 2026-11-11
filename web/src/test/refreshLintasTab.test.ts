import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type Client = typeof import("@/lib/apiClient");

// --- peniru lingkungan browser yang dipakai bersama oleh semua "tab" (instans modul) ---
class FakeChannel {
  static all = new Set<FakeChannel>();
  onmessage: ((ev: MessageEvent) => void) | null = null;
  constructor(public name: string) {
    FakeChannel.all.add(this);
  }
  postMessage(data: unknown) {
    for (const c of FakeChannel.all) {
      if (c !== this && c.name === this.name) setTimeout(() => c.onmessage?.({ data } as MessageEvent), 0);
    }
  }
  close() {
    FakeChannel.all.delete(this);
  }
}

let tail: Promise<unknown> = Promise.resolve();
const fakeLocks = {
  request: <T>(_name: string, cb: () => Promise<T>): Promise<T> => {
    const run = tail.then(cb, cb);
    tail = run.catch(() => undefined);
    return run;
  },
};

// --- peniru server: cookie refresh dipakai bersama; token lama dipakai lagi = reuse ---
let cookie = "c0";
let rotations = 0;
let reuseDetected = 0;

function fakeServerRefresh() {
  return vi.spyOn(axios, "post").mockImplementation(async () => {
    const sent = cookie; // browser mengirim cookie saat request dibuat
    await new Promise((r) => setTimeout(r, 15));
    if (sent !== cookie) {
      reuseDetected += 1;
      throw new axios.AxiosError("reuse", "401", undefined, null, { status: 401 } as never);
    }
    rotations += 1;
    cookie = `c${rotations}`;
    return { data: { access_token: `token-${rotations}` } };
  });
}

async function newTab(): Promise<Client> {
  vi.resetModules();
  return import("@/lib/apiClient");
}

beforeEach(() => {
  cookie = "c0";
  rotations = 0;
  reuseDetected = 0;
  FakeChannel.all.clear();
  tail = Promise.resolve();
  vi.stubGlobal("BroadcastChannel", FakeChannel);
  Object.defineProperty(navigator, "locks", { value: fakeLocks, configurable: true });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  Reflect.deleteProperty(navigator, "locks");
});

describe("refresh lintas tab", () => {
  it("dua tab refresh bersamaan tidak memicu pemakaian ulang cookie refresh", async () => {
    fakeServerRefresh();
    const tabA = await newTab();
    const tabB = await newTab();
    const [a, b] = await Promise.allSettled([tabA.refreshAccessToken(), tabB.refreshAccessToken()]);
    expect(reuseDetected).toBe(0);
    expect(a.status).toBe("fulfilled");
    expect(b.status).toBe("fulfilled");
  });

  it("tab yang menunggu memakai hasil tab lain (satu rotasi saja)", async () => {
    const post = fakeServerRefresh();
    const tabA = await newTab();
    const tabB = await newTab();
    const [a, b] = await Promise.all([tabA.refreshAccessToken(), tabB.refreshAccessToken()]);
    expect(post).toHaveBeenCalledTimes(1);
    expect(a).toBe("token-1");
    expect(b).toBe("token-1");
    expect(tabB.getAccessToken()).toBe("token-1");
  });

  it("token tidak disimpan di localStorage", async () => {
    fakeServerRefresh();
    const tabA = await newTab();
    await tabA.refreshAccessToken();
    const dump = JSON.stringify(Object.entries(localStorage));
    expect(dump).not.toContain("token-1");
  });

  it("logout satu tab disiarkan ke tab lain", async () => {
    const tabB = await newTab();
    const keluar = vi.fn();
    tabB.setLogoutBroadcastReceiver(keluar);
    vi.resetModules();
    const tabA = await import("@/lib/tabSync"); // instans lain = tab lain
    tabA.broadcastLogout();
    await new Promise((r) => setTimeout(r, 10));
    expect(keluar).toHaveBeenCalled();
  });
});
