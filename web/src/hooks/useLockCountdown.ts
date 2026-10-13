import { useEffect, useState } from "react";

/** Hitung mundur cooldown login (R-21) dari `retry_after_seconds` server; server tetap penentunya. */
export function useLockCountdown() {
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (until <= now) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [until, now]);
  return {
    seconds: Math.max(0, Math.ceil((until - now) / 1000)),
    start: (secs: number) => {
      const t = Date.now();
      setNow(t);
      setUntil(t + secs * 1000);
    },
  };
}
