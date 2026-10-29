import { renderHook, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { parsePage, useListControls } from "@/hooks/useListControls";
import { useClientList } from "@/hooks/useClientList";
import { lastPageOf } from "@/lib/paged";

const wrap = (url: string) => ({ children }: { children: ReactNode }) => <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>;
const items = Array.from({ length: 45 }, (_, i) => ({ name: i === 7 ? "Tim Álfa" : `Tim ${i}` }));

describe("parsePage", () => {
  it("menolak nilai tidak valid dari URL", () => {
    for (const bad of [null, "", "0", "-3", "abc", "1.5", "999999"]) expect(parsePage(bad)).toBe(1);
    expect(parsePage("3")).toBe(3);
  });
});

describe("useClientList", () => {
  it("memotong 20 per halaman dan menghitung halaman terakhir", () => {
    const { result } = renderHook(() => useClientList(items, (t) => [t.name]), { wrapper: wrap("/?page=3") });
    expect(result.current.total).toBe(45);
    expect(result.current.lastPage).toBe(3);
    expect(result.current.rows).toHaveLength(5);
  });

  it("halaman di luar jangkauan dipaksa ke halaman terakhir", () => {
    const { result } = renderHook(() => useClientList(items, (t) => [t.name]), { wrapper: wrap("/?page=50") });
    expect(result.current.shownPage).toBe(3);
  });

  it("mencari tanpa beda huruf besar dan aksen", async () => {
    const { result } = renderHook(() => useClientList(items, (t) => [t.name]), { wrapper: wrap("/") });
    act(() => result.current.setInput("ALFA"));
    await new Promise((r) => setTimeout(r, 450));
    expect(result.current.total).toBe(0 + 1);
  });
});

describe("lastPageOf", () => {
  it("minimal 1", () => {
    expect(lastPageOf(undefined)).toBe(1);
    expect(lastPageOf({ total: 0, size: 20 })).toBe(1);
    expect(lastPageOf({ total: 41, size: 20 })).toBe(3);
  });
});

describe("pagedView", () => {
  it("memetakan hasil server ke baris, total, dan halaman terakhir", async () => {
    const { pagedView } = await import("@/hooks/usePagedList");
    const { result } = renderHook(
      () => {
        const c = useListControls({ size: 20, prefix: "t_" });
        return pagedView(
          { data: { items: [{ a: 1 }, { a: 2 }], total: 45, page: 2, size: 20 } } as never,
          c,
        );
      },
      { wrapper: wrap("/?t_page=2") },
    );
    expect(result.current.rows).toHaveLength(2);
    expect(result.current.total).toBe(45);
    expect(result.current.lastPage).toBe(3);
    expect(result.current.shownPage).toBe(2);
  });
});
