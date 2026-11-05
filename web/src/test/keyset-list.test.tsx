import { QueryClient, QueryClientProvider, focusManager } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { StrictMode } from "react";
import { describe, expect, it } from "vitest";
import { useKeysetList } from "@/hooks/useKeysetList";
import { apiError, mockApi } from "./utils";

type Row = { id: string };
const PARAMS = { size: 2 };

function setup() {
  // Default sengaja agresif (staleTime 0, fokus aktif) untuk membuktikan hook menimpanya.
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0, refetchOnWindowFocus: true } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <StrictMode>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </StrictMode>
  );
  const useSubject = () =>
    useKeysetList<Row[], Row[]>({ key: ["t"], url: "/t", params: { ...PARAMS }, merge: (p) => p.flat() });
  return { client, wrapper, hook: useSubject };
}

describe("useKeysetList", () => {
  it("memanggil API sekali per halaman, tanpa mengulang halaman sebelumnya, dan fokus tidak memuat ulang", async () => {
    const calls = mockApi((c) => {
      const cur = (c.params as { cursor: string }).cursor;
      if (cur === "") return { data: [{ id: "1" }, { id: "2" }], headers: { "x-next-cursor": "c2" } };
      if (cur === "c2") return { data: [{ id: "3" }, { id: "4" }], headers: { "x-next-cursor": "c3" } };
      return { data: [{ id: "5" }] };
    });
    const { wrapper, hook } = setup();
    const { result } = renderHook(hook, { wrapper });
    await waitFor(() => expect(result.current.query.data).toHaveLength(2));
    expect(calls).toHaveLength(1);

    await act(async () => result.current.more.onLoadMore());
    await waitFor(() => expect(result.current.query.data).toHaveLength(4));
    await act(async () => result.current.more.onLoadMore());
    await waitFor(() => expect(result.current.query.data).toHaveLength(5));
    expect(calls.map((c) => (c.params as { cursor: string }).cursor)).toEqual(["", "c2", "c3"]);

    await act(async () => {
      focusManager.setFocused(false);
      focusManager.setFocused(true);
    });
    expect(calls).toHaveLength(3);
    expect(result.current.more.hasMore).toBe(false);
  });

  it("422 pada kursor memulai ulang dari halaman pertama dan menampilkan catatan", async () => {
    let fail = true;
    const calls = mockApi((c) => {
      const cur = (c.params as { cursor: string }).cursor;
      if (cur === "") return { data: [{ id: "1" }], headers: { "x-next-cursor": "bad" } };
      if (fail) {
        fail = false;
        return apiError(422, "VALIDATION_ERROR", "Kursor tidak valid.");
      }
      return { data: [] };
    });
    const { wrapper, hook } = setup();
    const { result } = renderHook(hook, { wrapper });
    await waitFor(() => expect(result.current.query.data).toHaveLength(1));
    await act(async () => result.current.more.onLoadMore());
    await waitFor(() => expect(result.current.more.notice).not.toBeNull());
    await waitFor(() => expect(calls.filter((c) => (c.params as { cursor: string }).cursor === "").length).toBeGreaterThanOrEqual(2));
    expect(result.current.query.data).toHaveLength(1);
  });
});
