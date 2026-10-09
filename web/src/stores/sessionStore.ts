import { create } from "zustand";
import { refreshAccessToken, setAccessToken, setSessionExpiredHandler } from "@/lib/apiClient";
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

export const useSession = create<SessionState>((set, get) => {
  const skipRestore = import.meta.env.DEV && !!import.meta.env.VITE_MOCK_ROLE;
  const preset = skipRestore ? mockMe(import.meta.env.VITE_MOCK_ROLE) : null;

  const clear = () => {
    setAccessToken(null);
    set({ me: null });
    queryClient.clear();
  };

  setSessionExpiredHandler(clear);

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
      setAccessToken(token.access_token);
      const profile = await fetchMe();
      set({ me: profile });
      return profile;
    },
    initSession: async () => {
      if (get().ready) return;
      try {
        // Lewat refresh tunggal: efek ganda (StrictMode) atau request paralel tidak boleh merotasi
        // cookie dua kali — refresh kedua memakai token lama dan sesi ikut dicabut.
        await refreshAccessToken();
        set({ me: await fetchMe() });
      } catch {
        /* belum login */
      } finally {
        set({ ready: true });
      }
    }
  };
});

