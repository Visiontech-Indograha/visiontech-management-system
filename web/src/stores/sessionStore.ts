import { create } from "zustand";
import { getAccessToken, refreshAccessToken, setAccessToken, setSessionExpiredHandler } from "@/lib/apiClient";
import type { Me, TokenOut } from "@/lib/types";
import { mockMe } from "../app/mockSession";
import { queryClient } from "@/lib/queryClient";
import { fetchMe, login as authLogin, logout as authLogout } from "@/services/authService";

interface SessionState {
  me: Me | null;
  /** false selama sesi dipulihkan dari cookie refresh saat aplikasi dibuka. */
  ready: boolean;
  login: (email: string, password: string, admin?: boolean) => Promise<Me>;
  logout: () => Promise<void>;
  /** Terapkan token baru (mis. setelah ganti password) lalu muat ulang /auth/me. */
  applyToken: (token: TokenOut) => Promise<Me>;
  initSession: () => Promise<void>;
}

function parseAuthTime(token: string | null): number | null {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const payload = JSON.parse(
      atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")),
    ) as Record<string, unknown>;
    return typeof payload.auth_time === "number" ? payload.auth_time : null;
  } catch {
    return null;
  }
}

/** Mengecek apakah sesi sudah melewati batas 24 jam absolut (86400 detik) sesuai aturan backend. */
function isSessionExpired(authTimeSec: number | null): boolean {
  if (!authTimeSec) return false;
  const loginDate = new Date(authTimeSec * 1000);
  const now = new Date();
  return now.getTime() - loginDate.getTime() >= 24 * 3600 * 1000;
}

let initSessionPromise: Promise<void> | null = null;

export const useSession = create<SessionState>((set, get) => {
  const skipRestore = import.meta.env.DEV && !!import.meta.env.VITE_MOCK_ROLE;
  const preset = skipRestore ? mockMe(import.meta.env.VITE_MOCK_ROLE) : null;

  const clear = () => {
    setAccessToken(null);
    set({ me: null });
    queryClient.clear();
  };

  setSessionExpiredHandler(clear);

  // Monitor periodik & fokus jendela untuk auto-logout saat sesi melampaui 24 jam
  if (typeof window !== "undefined" && import.meta.env.MODE !== "test") {
    const checkExpiration = () => {
      const token = getAccessToken();
      if (token && isSessionExpired(parseAuthTime(token))) {
        clear();
      }
    };
    window.addEventListener("focus", checkExpiration);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") checkExpiration();
    });
    setInterval(checkExpiration, 60000);
  }

  return {
    me: preset,
    ready: skipRestore,
    login: async (email, password, admin = false) => {
      // Admin dan pengguna biasa memakai endpoint yang sama; `admin` hanya membedakan halaman login.
      void admin;
      return get().applyToken(await authLogin(email, password));
    },
    logout: async () => {
      try {
        await authLogout();
      } catch {
        /* sesi lokal tetap dibersihkan */
      }
      clear();
    },
    applyToken: async (token: TokenOut) => {
      if (isSessionExpired(parseAuthTime(token.access_token))) {
        clear();
        throw new Error("Sesi telah kedaluwarsa (maksimal 24 jam).");
      }
      setAccessToken(token.access_token);
      const profile = await fetchMe();
      set({ me: profile, ready: true });
      return profile;
    },
    initSession: async () => {
      if (get().ready || getAccessToken()) return;
      if (initSessionPromise) return initSessionPromise;

      initSessionPromise = (async () => {
        try {
          // Lewat refresh tunggal: efek ganda (StrictMode) atau request paralel tidak boleh merotasi
          // cookie dua kali — refresh kedua memakai token lama dan sesi ikut dicabut.
          const token = await refreshAccessToken();
          if (isSessionExpired(parseAuthTime(token))) {
            clear();
            return;
          }
          setAccessToken(token);
          const profile = await fetchMe();
          set({ me: profile });
        } catch {
          /* belum login atau refresh cookie tidak valid */
          clear();
        } finally {
          set({ ready: true });
          initSessionPromise = null;
        }
      })();

      return initSessionPromise;
    },
  };
});

