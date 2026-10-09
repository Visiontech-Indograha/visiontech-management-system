import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";
import { api, getAccessToken, refreshAccessToken } from "@/lib/apiClient";

/** Jeda sambung ulang bertingkat (ms): 1 → 2 → 5 → 15 → 30 detik. */
const RETRY_MS = [1000, 2000, 5000, 15000, 30000];

type LiveEvent = { topic: string; data: Record<string, unknown> };

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve) => {
    const t = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => (clearTimeout(t), resolve()), { once: true });
  });

function parseBlock(block: string): LiveEvent | null {
  let topic = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) topic = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trim());
  }
  if (data.length === 0) return null; // komentar ": ping"
  try {
    return { topic, data: JSON.parse(data.join("\n")) as Record<string, unknown> };
  } catch {
    return null;
  }
}

function handle(qc: QueryClient, ev: LiveEvent) {
  if (ev.topic === "notification") {
    void qc.invalidateQueries({ queryKey: ["notifications"] });
    toast(String(ev.data.title ?? "Notifikasi baru"), { description: String(ev.data.body ?? "") });
  } else if (ev.topic === "plan") {
    // Daftar, detail, perubahan, dokumen, hari, dan riwayat revisi: semua kunci yang diawali "work-plan"/"plan-".
    void qc.invalidateQueries({
      predicate: (q) => typeof q.queryKey[0] === "string" && /^(work-plans?|plan-)/.test(q.queryKey[0]),
    });
  } else if (ev.topic === "attendance") {
    void qc.invalidateQueries({ queryKey: ["attendance"] });
    void qc.invalidateQueries({ queryKey: ["attendance-recap"] });
  }
}

/**
 * Sambungan SSE ke GET /events (T8): menyegarkan data dan menampilkan toast tanpa muat ulang. Token dan refresh
 * memakai klien `api` yang sama. Putus → sambung ulang bertingkat; 401 → refresh token lalu sambung lagi.
 * Polling 60 detik di lonceng tetap menjadi cadangan.
 */
export function useLiveEvents(enabled = true) {
  const qc = useQueryClient();
  useEffect(() => {
    if (!enabled || import.meta.env.MODE === "test" || typeof fetch !== "function") return;
    const ctrl = new AbortController();
    const { signal } = ctrl;
    let attempt = 0;

    const run = async () => {
      while (!signal.aborted) {
        try {
          const token = getAccessToken();
          if (!token) {
            await sleep(RETRY_MS[0], signal);
            continue;
          }
          const res = await fetch(`${api.defaults.baseURL ?? ""}/events`, {
            headers: { Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
            signal,
          });
          if (res.status === 401) {
            await refreshAccessToken();
          } else if (res.ok && res.body) {
            attempt = 0;
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            for (;;) {
              const { done, value } = await reader.read();
              if (done) break;
              buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
              let cut = buffer.indexOf("\n\n");
              while (cut >= 0) {
                const ev = parseBlock(buffer.slice(0, cut));
                buffer = buffer.slice(cut + 2);
                if (ev) handle(qc, ev);
                cut = buffer.indexOf("\n\n");
              }
            }
          }
        } catch {
          if (signal.aborted) return;
        }
        await sleep(RETRY_MS[Math.min(attempt++, RETRY_MS.length - 1)], signal);
      }
    };
    void run();
    return () => ctrl.abort();
  }, [enabled, qc]);
}
