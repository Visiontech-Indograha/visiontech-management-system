import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import axios from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, getAccessToken, setAccessToken, setSessionExpiredHandler } from "@/lib/apiClient";

function reply(config: InternalAxiosRequestConfig, status: number, data: unknown): Promise<AxiosResponse> {
  const response = { data, status, statusText: "", headers: {}, config } as AxiosResponse;
  if (status >= 200 && status < 300) return Promise.resolve(response);
  return Promise.reject(new axios.AxiosError("err", String(status), config, null, response));
}

afterEach(() => {
  vi.restoreAllMocks();
  setAccessToken(null);
  setSessionExpiredHandler(null);
});

describe("api client", () => {
  it("memetakan error seragam backend menjadi ApiError", async () => {
    api.defaults.adapter = ((c: InternalAxiosRequestConfig) =>
      reply(c, 409, { error: { code: "PLAN_CLOSED", message: "Work plan sudah ditutup.", details: { a: 1 } } })) as AxiosAdapter;
    const err = await api.get("/x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ code: "PLAN_CLOSED", status: 409, details: { a: 1 } });
  });

  it("401 → refresh sekali (single-flight) → ulangi request dengan token baru", async () => {
    setAccessToken("lama");
    const refresh = vi.spyOn(axios, "post").mockResolvedValue({ data: { access_token: "baru" } });
    const seen: string[] = [];
    api.defaults.adapter = ((c: InternalAxiosRequestConfig) => {
      const auth = String(c.headers.Authorization);
      seen.push(auth);
      return auth === "Bearer baru" ? reply(c, 200, { ok: true }) : reply(c, 401, { error: { code: "UNAUTHENTICATED", message: "x", details: {} } });
    }) as AxiosAdapter;

    const [a, b] = await Promise.all([api.get("/a"), api.get("/b")]);
    expect(a.data).toEqual({ ok: true });
    expect(b.data).toEqual({ ok: true });
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBe("baru");
    expect(seen.filter((s) => s === "Bearer lama")).toHaveLength(2);
  });

  it("refresh gagal → sesi berakhir dan error diteruskan", async () => {
    setAccessToken("lama");
    vi.spyOn(axios, "post").mockRejectedValue(new Error("refresh ditolak"));
    const expired = vi.fn();
    setSessionExpiredHandler(expired);
    api.defaults.adapter = ((c: InternalAxiosRequestConfig) =>
      reply(c, 401, { error: { code: "UNAUTHENTICATED", message: "x", details: {} } })) as AxiosAdapter;
    await expect(api.get("/a")).rejects.toMatchObject({ code: "UNAUTHENTICATED" });
    expect(expired).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBeNull();
  });

  it("login yang gagal 401 tidak memicu refresh", async () => {
    const refresh = vi.spyOn(axios, "post");
    api.defaults.adapter = ((c: InternalAxiosRequestConfig) =>
      reply(c, 401, { error: { code: "INVALID_CREDENTIALS", message: "x", details: {} } })) as AxiosAdapter;
    await expect(api.post("/auth/login", {})).rejects.toMatchObject({ code: "INVALID_CREDENTIALS" });
    expect(refresh).not.toHaveBeenCalled();
  });
});
