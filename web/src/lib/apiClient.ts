import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

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

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
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
  refreshing ??= axios
    .post<{ access_token: string }>(`${baseURL}/auth/refresh`, null, { withCredentials: true })
    .then((r) => {
      accessToken = r.data.access_token;
      return accessToken;
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
    return Promise.reject(toApiError(error));
  },
);
