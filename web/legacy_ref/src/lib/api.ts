import axios from "axios";
import toast from "react-hot-toast";

declare module "axios" {
  export interface AxiosRequestConfig {
    /** Lewati toast error global — dipakai untuk lookup yang wajar 404 (bukan error sungguhan). */
    suppressErrorToast?: boolean;
  }
}

// Jangan hardcode! Selalu gunakan import.meta.env
const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = axios.create({
  baseURL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * FastAPI mengirim `detail` sebagai string untuk HTTPException biasa, tapi sebagai
 * array objek `{loc, msg, type}` untuk error validasi Pydantic (422). Tanpa ini,
 * `${detail}` pada array objek menghasilkan "[object Object]" yang tidak berguna.
 */
function extractErrorMessage(data: unknown): string {
  const detail = (data as { detail?: unknown; message?: unknown })?.detail
    ?? (data as { message?: unknown })?.message;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const loc = Array.isArray((item as { loc?: unknown[] }).loc)
            ? (item as { loc: unknown[] }).loc.filter((l) => l !== "body").join(".")
            : undefined;
          const msg = String((item as { msg: unknown }).msg);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return null;
      })
      .filter((m): m is string => !!m);
    if (messages.length) return messages.join("; ");
  }

  return "Terjadi kesalahan pada server.";
}

let memoryToken: string | null = null;

export const setMemoryToken = (token: string | null) => {
  memoryToken = token;
};

api.interceptors.request.use(
  (config) => {
    if (memoryToken && config.headers) {
      config.headers.Authorization = `Bearer ${memoryToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    // `/auth/me` adalah probe sesi saat boot: 401 di sini bisa berarti "belum pernah login"
    // (bukan sesi kedaluwarsa). Tetap coba refresh sekali, tapi kalau gagal jangan tampilkan
    // toast "sesi habis" atau redirect paksa — cukup reject dan biarkan AuthContext + router
    // yang mengarahkan ke /login.
    const isAuthProbe = originalRequest?.url?.includes("/api/v1/auth/me");
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      window.location.pathname !== "/login"
    ) {
      originalRequest._retry = true;
      try {
        const res = await axios.post(`${baseURL}/api/v1/auth/refresh`, {}, { withCredentials: true });
        const newToken = res.data.access_token;
        setMemoryToken(newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        setMemoryToken(null);
        if (!isAuthProbe) {
          toast.error("Sesi telah habis. Silakan login kembali.");
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      }
    }

    if (error.response) {
      if (error.response.status !== 401 && !originalRequest?.suppressErrorToast) {
        toast.error(`Error: ${extractErrorMessage(error.response.data)}`);
      }
    } else if (error.request) {
      toast.error("Tidak dapat terhubung ke server. Periksa koneksi internet Anda.");
    } else {
      toast.error("Terjadi kesalahan sistem.");
    }
    return Promise.reject(error);
  }
);

export default api;
