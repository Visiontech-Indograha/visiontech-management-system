import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

const asked: unknown[][] = [];
let fail = false;
vi.mock("@/services/fileService", () => ({
  fetchFileUrl: async (...a: unknown[]) => {
    asked.push(a);
    if (fail) throw new Error("x");
    return { url: "https://s/doc.pdf" };
  },
}));

import { DocumentLink } from "./DocumentLink";

const wrap = (ui: React.ReactElement) =>
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>);

describe("DocumentLink", () => {
  beforeEach(() => {
    asked.length = 0;
    fail = false;
  });

  it("menampilkan tautan buka dokumen dari URL bertiket", async () => {
    wrap(<DocumentLink fileId="f1" label="Buka dokumen serah terima" />);
    const a = await screen.findByRole("link", { name: "Buka dokumen serah terima" });
    expect(a).toHaveAttribute("href", "https://s/doc.pdf");
    expect(asked[0]).toEqual(["f1", "full"]);
  });

  it("memberi tahu bila dokumen tak bisa dibuka", async () => {
    fail = true;
    wrap(<DocumentLink fileId="f1" label="Buka dokumen serah terima" />);
    expect(await screen.findByText(/belum bisa dibuka/)).toBeInTheDocument();
  });
});
