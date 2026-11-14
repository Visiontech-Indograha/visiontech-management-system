import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

type Opsi = { params: Record<string, unknown> };
const calls: Opsi[] = [];
vi.mock("@/lib/apiClient", () => ({
  api: {
    get: async (_url: string, o: Opsi) => {
      calls.push(o);
      return { data: [] };
    },
  },
}));

import { useBorrowerOptions } from "@/services/assetService";

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{children}</QueryClientProvider>
);

describe("useBorrowerOptions", () => {
  beforeEach(() => {
    calls.length = 0;
  });

  it("menyaring penerima ke kantor aset", async () => {
    const { result } = renderHook(() => useBorrowerOptions("", true, "kantor-1"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(calls[0].params.office_id).toBe("kantor-1");
  });
});
