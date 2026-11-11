import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { listenTabSync, refreshAcrossTabs } from "@/lib/tabSync";

/** Bentuk error seragam dari backend (docs/05-API-SPEC §4). */
export class ApiError extends Error {
  code: string;
  status: number;
  details: Record<string, unknown>;

  constructor(code: string, message: string, status: number, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

/** Kosong = same-origin (Caddy / Vite proxy meneruskan /api). */
const baseURL = `${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1`;

export const api = axios.create({ baseURL, withCredentials: true });

// --- token akses hanya di memori (refresh lewat cookie HttpOnly di web, D-25) ---
let accessToken: string | null = null;
let onSessionExpired: (() => void) | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
};
export const getAccessToken = () => accessToken;
export const setSessionExpiredHandler = (fn: (() => void) | null) => {
  onSessionExpired = fn;
};

// Siaran dari tab lain: token baru hanya diterima bila tab ini sudah punya sesi (tetap di memori).
let onRemoteLogout: (() => void) | null = null;
export const setLogoutBroadcastReceiver = (fn: (() => void) | null) => {
  onRemoteLogout = fn;
};
listenTabSync({
  onToken: (token) => {
    if (accessToken) accessToken = token;
  },
  onLogout: () => onRemoteLogout?.(),
});

/** Penanda kemampuan klien: server baru menjawab 403 MUST_CHANGE_PASSWORD bila sandi sementara belum diganti. */
export const APP_CAPABILITIES = "must-change-password";
let onMustChangePassword: (() => void) | null = null;
export const setMustChangePasswordHandler = (fn: (() => void) | null) => {
  onMustChangePassword = fn;
};

function getOrCreateDeviceFingerprint(): string {
  if (typeof window === "undefined") return "web-client";
  try {
    let fp = localStorage.getItem("vms_device_fingerprint");
    if (!fp) {
      fp = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `web-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
      localStorage.setItem("vms_device_fingerprint", fp);
    }
    return fp;
  } catch {
    return "web-client";
  }
}

function getDeviceLabel(): string {
  if (typeof navigator === "undefined" || !navigator.userAgent) return "Web Browser";
  const ua = navigator.userAgent;
  let browser = "Browser";
  if (ua.includes("Firefox")) browser = "Firefox";
  else if (ua.includes("Edg")) browser = "Edge";
  else if (ua.includes("Chrome")) browser = "Chrome";
  else if (ua.includes("Safari")) browser = "Safari";

  let os = "Desktop";
  if (ua.includes("Windows")) os = "Windows";
  else if (ua.includes("Mac OS")) os = "macOS";
  else if (ua.includes("Linux")) os = "Linux";
  else if (ua.includes("Android")) os = "Android";
  else if (ua.includes("iPhone") || ua.includes("iPad")) os = "iOS";

  return `${browser} on ${os}`;
}

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  config.headers["X-Device-Fingerprint"] = getOrCreateDeviceFingerprint();
  config.headers["X-Device-Label"] = getDeviceLabel();
  config.headers["X-App-Capabilities"] = APP_CAPABILITIES;
  return config;
});

function toApiError(error: AxiosError): ApiError {
  const body = error.response?.data as
    | { error?: { code?: string; message?: string; details?: Record<string, unknown> } }
    | undefined;
  if (body?.error?.code) {
    return new ApiError(
      body.error.code,
      body.error.message ?? "Terjadi kesalahan.",
      error.response!.status,
      body.error.details,
    );
  }
  if (!error.response) {
    return new ApiError("NETWORK_ERROR", "Tidak ada koneksi ke server.", 0);
  }
  return new ApiError("UNKNOWN_ERROR", "Terjadi kesalahan pada server.", error.response.status);
}

// Satu refresh berjalan pada satu waktu; request lain menunggu hasilnya (rotasi refresh token).
let refreshing: Promise<string> | null = null;

export async function refreshAccessToken(): Promise<string> {
  // Lintas tab: kunci "vms-refresh" mencegah dua tab memakai cookie refresh yang sama bersamaan
  // (refresh kedua dianggap pemakaian ulang dan mencabut semua sesi).
  refreshing ??= refreshAcrossTabs(() =>
    axios
      .post<{ access_token: string }>(
        `${baseURL}/auth/refresh`,
        null,
        {
          withCredentials: true,
          headers: {
            "X-Device-Fingerprint": getOrCreateDeviceFingerprint(),
            "X-Device-Label": getDeviceLabel(),
            "X-App-Capabilities": APP_CAPABILITIES,
          },
        },
      )
      .then((r) => r.data.access_token),
  )
    .then((token) => {
      accessToken = token;
      return token;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

const AUTH_PATHS = ["/auth/login", "/auth/admin-login", "/auth/refresh", "/auth/logout"];

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const isAuthCall = AUTH_PATHS.some((p) => original?.url?.includes(p));

    if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true;
      try {
        const token = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      } catch {
        setAccessToken(null);
        onSessionExpired?.();
      }
    }
    const apiError = toApiError(error);
    if (apiError.status === 403 && apiError.code === "MUST_CHANGE_PASSWORD") onMustChangePassword?.();
    return Promise.reject(apiError);
  },
);
