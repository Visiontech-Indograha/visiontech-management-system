import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setAccessToken, setSessionExpiredHandler } from "@/lib/api";
import type { Me, TokenOut } from "@/lib/types";
import { mockMe } from "./mockSession";

interface SessionValue {
  me: Me | null;
  /** false selama sesi dipulihkan dari cookie refresh saat aplikasi dibuka. */
  ready: boolean;
  can: (...perms: string[]) => boolean;
  login: (username: string, password: string, admin?: boolean) => Promise<Me>;
  logout: () => Promise<void>;
  /** Terapkan token baru (mis. setelah ganti password) lalu muat ulang /me. */
  applyToken: (token: TokenOut) => Promise<Me>;
}

const SessionContext = createContext<SessionValue | null>(null);

async function fetchMe(): Promise<Me> {
  return (await api.get<Me>("/me")).data;
}

export function SessionProvider({ children, initial }: { children: ReactNode; initial?: Me | null }) {
  // `initial` (test) dan VITE_MOCK_ROLE (pratinjau dev) melewati pemulihan sesi.
  const preset = initial !== undefined ? initial : import.meta.env.DEV ? mockMe(import.meta.env.VITE_MOCK_ROLE) : null;
  const skipRestore = initial !== undefined || preset !== null;
  const [me, setMe] = useState<Me | null>(preset);
  const [ready, setReady] = useState(skipRestore);
  const queryClient = useQueryClient();

  const clear = useCallback(() => {
    setAccessToken(null);
    setMe(null);
    queryClient.clear();
  }, [queryClient]);

  // Pulihkan sesi dari cookie refresh HttpOnly.
  useEffect(() => {
    if (skipRestore) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.post<TokenOut>("/auth/refresh");
        setAccessToken(data.access_token);
        const profile = await fetchMe();
        if (!cancelled) setMe(profile);
      } catch {
        /* belum login */
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [skipRestore]);

  useEffect(() => {
    setSessionExpiredHandler(clear);
    return () => setSessionExpiredHandler(null);
  }, [clear]);

  const applyToken = useCallback(async (token: TokenOut) => {
    setAccessToken(token.access_token);
    const profile = await fetchMe();
    setMe(profile);
    return profile;
  }, []);

  const value = useMemo<SessionValue>(
    () => ({
      me,
      ready,
      can: (...perms) => !!me && perms.every((p) => me.permissions.includes(p)),
      login: async (username, password, admin = false) => {
        const { data } = await api.post<TokenOut>(admin ? "/auth/admin-login" : "/auth/login", {
          username,
          password,
          platform: "web",
        });
        return applyToken(data);
      },
      logout: async () => {
        try {
          await api.post("/auth/logout");
        } catch {
          /* sesi lokal tetap dibersihkan */
        }
        clear();
      },
      applyToken,
    }),
    [me, ready, applyToken, clear],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSession(): SessionValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession harus di dalam SessionProvider");
  return ctx;
}
