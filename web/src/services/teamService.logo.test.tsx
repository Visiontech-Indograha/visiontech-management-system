import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { api } from "@/lib/apiClient";
import { useTeamLogo } from "./teamService";

vi.mock("@/lib/apiClient", () => ({
  api: { get: vi.fn() },
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useTeamLogo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:logo-tim") });
  });

  it("mengunduh logo lewat API (berkas terautentikasi) lalu memberi object URL", async () => {
    const blob = new Blob(["png"], { type: "image/png" });
    vi.mocked(api.get).mockResolvedValue({ data: blob });
    const { result } = renderHook(() => useTeamLogo("t1", true), { wrapper });
    await waitFor(() => expect(result.current.data).toBe("blob:logo-tim"));
    expect(api.get).toHaveBeenCalledWith("/teams/t1/logo", { responseType: "blob" });
  });

  it("tidak meminta logo bila tim belum punya logo", () => {
    renderHook(() => useTeamLogo("t1", false), { wrapper });
    expect(api.get).not.toHaveBeenCalled();
  });
});
