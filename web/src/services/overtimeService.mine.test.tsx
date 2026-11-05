import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { api } from "@/lib/apiClient";
import { useMyOvertime, useOvertimePending } from "./overtimeService";

vi.mock("@/lib/apiClient", () => ({
  api: { get: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const row = (id: string, employee_id: string) => ({ id, employee_id });

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe("lembur: mine", () => {
  beforeEach(() => vi.clearAllMocks());

  it("Lembur saya mengirim mine=true dan tidak menyaring di klien", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [row("a", "e1"), row("b", "e2")], headers: {} });
    const { wrapper } = setup();
    const { result } = renderHook(() => useMyOvertime(), { wrapper });
    await waitFor(() => expect(result.current.query.data).toHaveLength(2));
    expect(vi.mocked(api.get).mock.calls[0][1]).toMatchObject({ params: { mine: true } });
  });

  it("daftar peninjau tanpa mine", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [], headers: {} });
    const { wrapper } = setup();
    const { result } = renderHook(() => useOvertimePending(), { wrapper });
    await waitFor(() => expect(result.current.query.isSuccess).toBe(true));
    const params = (vi.mocked(api.get).mock.calls[0][1] as { params: Record<string, unknown> }).params;
    expect(params).not.toHaveProperty("mine");
  });

  it("halaman berikutnya memakai mine yang sama", async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: [row("a", "e1")], headers: { "x-next-cursor": "c1" } })
      .mockResolvedValueOnce({ data: [row("b", "e1")], headers: {} });
    const { wrapper } = setup();
    const { result } = renderHook(() => useMyOvertime(), { wrapper });
    await waitFor(() => expect(result.current.more.hasMore).toBe(true));
    result.current.more.onLoadMore();
    await waitFor(() => expect(result.current.query.data).toHaveLength(2));
    expect(vi.mocked(api.get).mock.calls[1][1]).toMatchObject({ params: { mine: true, cursor: "c1" } });
  });

  it("kunci cache terpisah dari antrean peninjau", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [], headers: {} });
    const { client, wrapper } = setup();
    renderHook(() => ({ a: useMyOvertime(), b: useOvertimePending() }), { wrapper });
    await waitFor(() => expect(client.getQueryCache().getAll()).toHaveLength(2));
    const keys = client.getQueryCache().getAll().map((q) => JSON.stringify(q.queryKey));
    expect(new Set(keys).size).toBe(2);
    expect(keys.some((k) => k.includes('"mine":true'))).toBe(true);
  });
});
