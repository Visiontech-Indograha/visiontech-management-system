import { create } from "zustand";
import {
  getAccessToken,
  refreshAccessToken,
  setAccessToken,
  setLogoutBroadcastReceiver,
  setMustChangePasswordHandler,
  setSessionExpiredHandler,
} from "@/lib/apiClient";
import { broadcastLogout } from "@/lib/tabSync";
import type { Me, TokenOut } from "@/lib/types";
import { mockMe } from "../app/mockSession";
import { queryClient } from "@/lib/queryClient";
import { fetchMe, login as authLogin, logout as authLogout } from "@/services/authService";

interface SessionState {
  me: Me | null;
  activeDivisionId: string | null;
  setActiveDivisionId: (id: string | null) => void;
  /** false selama sesi dipulihkan dari cookie refresh saat aplikasi dibuka. */
  ready: boolean;
  login: (email: string, password: string, admin?: boolean) => Promise<Me>;
  logout: () => Promise<void>;
  /** Terapkan token baru (mis. setelah ganti sandi) lalu muat ulang /auth/me. */
  applyToken: (token: TokenOut) => Promise<Me>;
  initSession: () => Promise<void>;
  /** Muat ulang /auth/me (mis. setelah foto profil diganti) tanpa mengubah token. */
  refreshMe: () => Promise<void>;
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
    set({ me: null, activeDivisionId: null });
    queryClient.clear();
  };

  setSessionExpiredHandler(clear);
  // Tab lain keluar: ikut keluar (tanpa menyiarkan ulang).
  setLogoutBroadcastReceiver(clear);
  // Server menjawab 403 MUST_CHANGE_PASSWORD: tandai sesi agar RequireAuth mengarahkan ke ganti sandi.
  setMustChangePasswordHandler(() => {
    const current = get().me;
    if (current && !current.must_change_password) set({ me: { ...current, must_change_password: true } });
  });

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
    activeDivisionId: preset?.division_id ?? null,
    setActiveDivisionId: (id: string | null) => set({ activeDivisionId: id }),
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
      broadcastLogout();
    },
    applyToken: async (token: TokenOut) => {
      if (isSessionExpired(parseAuthTime(token.access_token))) {
        clear();
        throw new Error("Sesi telah kedaluwarsa (maksimal 24 jam).");
      }
      setAccessToken(token.access_token);
      const profile = await fetchMe();
      set((s) => ({
        me: profile,
        ready: true,
        activeDivisionId: s.activeDivisionId || profile.division_id || profile.managed_division_ids?.[0] || null,
      }));
      return profile;
    },
    refreshMe: async () => {
      if (!getAccessToken()) return;
      const profile = await fetchMe();
      set((s) => ({
        me: profile,
        activeDivisionId: s.activeDivisionId || profile.division_id || profile.managed_division_ids?.[0] || null,
      }));
    },
    initSession: async () => {
      if (get().ready || getAccessToken()) return;
      if (initSessionPromise) return initSessionPromise;

      initSessionPromise = (async () => {
        try {
          if (getAccessToken() || get().me) return;
          // Lewat refresh tunggal: efek ganda (StrictMode) atau request paralel tidak boleh merotasi
          // cookie dua kali — refresh kedua memakai token lama dan sesi ikut dicabut.
          const token = await refreshAccessToken();
          if (getAccessToken() && getAccessToken() !== token) return;
          if (isSessionExpired(parseAuthTime(token))) {
            clear();
            return;
          }
          setAccessToken(token);
          const profile = await fetchMe();
          set({ me: profile });
        } catch {
          /* belum login atau refresh cookie tidak valid */
          if (!getAccessToken() && !get().me) {
            // Tidak ada sesi: jangan queryClient.clear() — itu memutus query publik yang sedang berjalan
            // (mis. GET /setup/status di halaman masuk dan /setup) sehingga tertahan "memuat" selamanya.
            setAccessToken(null);
            set({ me: null, activeDivisionId: null });
          }
        } finally {
          set({ ready: true });
          initSessionPromise = null;
        }
      })();

      return initSessionPromise;
    },
  };
});

