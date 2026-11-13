import { afterEach, describe, expect, it, vi } from "vitest";
import { setAccessToken } from "@/lib/apiClient";
import { useSession } from "./sessionStore";

vi.mock("axios", async (orig) => {
  const mod = await orig<typeof import("axios")>();
  return { ...mod, default: { ...mod.default, post: vi.fn(() => Promise.reject(new Error("401"))) } };
});

afterEach(() => setAccessToken(null));

describe("initSession tanpa sesi", () => {
  it("tidak memanggil /auth/refresh bila peramban belum pernah masuk", async () => {
    const axios = (await import("axios")).default;
    localStorage.clear();
    await useSession.getState().initSession();
    expect(axios.post).not.toHaveBeenCalled();
    expect(useSession.getState().ready).toBe(true);
  });
});
