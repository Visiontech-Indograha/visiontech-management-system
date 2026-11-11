// Koordinasi lintas tab: satu refresh pada satu waktu untuk seluruh tab (cookie refresh dipakai bersama,
// rotasi + deteksi pemakaian ulang di server). Token akses hanya disiarkan lewat BroadcastChannel dan
// tetap disimpan di memori — tidak pernah ditulis ke localStorage.

const LOCK_NAME = "vms-refresh";
const CHANNEL_NAME = "vms-session";
const FALLBACK_KEY = "vms-refresh-lock";
const FALLBACK_TTL_MS = 15000;
const BROADCAST_SETTLE_MS = 100;

type Message = { type: "token"; token: string } | { type: "logout" };

let channel: BroadcastChannel | null | undefined;
let lastReceived: { token: string; at: number } | null = null;
let onToken: ((token: string) => void) | null = null;
let onLogout: (() => void) | null = null;
const tabId = Math.random().toString(36).slice(2);

function getChannel(): BroadcastChannel | null {
  if (channel !== undefined) return channel;
  channel = null;
  if (typeof BroadcastChannel === "undefined") return channel;
  try {
    channel = new BroadcastChannel(CHANNEL_NAME);
    channel.onmessage = (ev: MessageEvent<Message>) => {
      const msg = ev.data;
      if (msg?.type === "token" && typeof msg.token === "string") {
        lastReceived = { token: msg.token, at: Date.now() };
        onToken?.(msg.token);
      } else if (msg?.type === "logout") {
        onLogout?.();
      }
    };
  } catch {
    channel = null;
  }
  return channel;
}

/** Pasang penerima siaran dari tab lain (token baru, keluar). */
export function listenTabSync(handlers: { onToken?: (t: string) => void; onLogout?: () => void }) {
  onToken = handlers.onToken ?? null;
  onLogout = handlers.onLogout ?? null;
  getChannel();
}

export function broadcastLogout() {
  getChannel()?.postMessage({ type: "logout" } satisfies Message);
}

async function withFallbackLock<T>(fn: () => Promise<T>): Promise<T> {
  const deadline = Date.now() + FALLBACK_TTL_MS;
  const mine = `${tabId}:${Date.now() + FALLBACK_TTL_MS}`;
  try {
    for (;;) {
      const cur = localStorage.getItem(FALLBACK_KEY);
      const expiry = cur ? Number(cur.split(":")[1]) : 0;
      if (!cur || expiry < Date.now()) {
        localStorage.setItem(FALLBACK_KEY, mine);
        await new Promise((r) => setTimeout(r, 20));
        if (localStorage.getItem(FALLBACK_KEY) === mine) break;
      }
      if (Date.now() > deadline) break;
      await new Promise((r) => setTimeout(r, 50));
    }
  } catch {
    return fn();
  }
  try {
    return await fn();
  } finally {
    try {
      if (localStorage.getItem(FALLBACK_KEY) === mine) localStorage.removeItem(FALLBACK_KEY);
    } catch {
      /* abaikan */
    }
  }
}

/**
 * Jalankan refresh dengan kunci lintas tab. Tab yang menunggu kunci memakai token hasil tab lain
 * (bila sudah disiarkan selama menunggu) tanpa memanggil server lagi.
 */
export async function refreshAcrossTabs(doRefresh: () => Promise<string>): Promise<string> {
  const ch = getChannel();
  const startedAt = Date.now();
  const run = async (): Promise<string> => {
    if (lastReceived && lastReceived.at >= startedAt) return lastReceived.token;
    const token = await doRefresh();
    ch?.postMessage({ type: "token", token } satisfies Message);
    // Tahan kunci sebentar agar siaran sampai ke tab yang menunggu sebelum mereka mengambil giliran.
    if (ch) await new Promise((r) => setTimeout(r, BROADCAST_SETTLE_MS));
    return token;
  };
  const locks = typeof navigator !== "undefined" ? navigator.locks : undefined;
  if (locks && typeof locks.request === "function") return locks.request(LOCK_NAME, run);
  return withFallbackLock(run);
}
