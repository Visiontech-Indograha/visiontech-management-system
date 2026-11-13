import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AttachmentPanel } from "./AttachmentPanel";
import { api } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", async (orig) => ({ ...(await orig<object>()), api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } }));
vi.mock("@/components/molecules/FilePreview", () => ({ FilePreview: () => <span>buka</span> }));

const item = (id: string, mine = true) => ({ file_id: id, file_name: `${id}.pdf`, mime_type: "application/pdf", byte_size: 2048, mine, created_at: "2026-01-01T00:00:00Z" });

const view = (locked = false) =>
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><AttachmentPanel kind="overtime" parentId="o1" locked={locked} /></QueryClientProvider>);

beforeEach(() => vi.clearAllMocks());

describe("AttachmentPanel", () => {
  it("kosong: tampil pesan dan kolom tambah", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    view();
    expect(await screen.findByText("Belum ada lampiran.")).toBeTruthy();
    expect(screen.getByLabelText("Tambah lampiran")).toBeTruthy();
  });
  it("galat: tampil Coba lagi", async () => {
    vi.mocked(api.get).mockRejectedValue(new Error("x"));
    view();
    expect(await screen.findByText("Lampiran tidak dapat dimuat.")).toBeTruthy();
  });
  it("terkunci: tombol tambah dan hapus tersembunyi", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [item("a")] });
    view(true);
    expect(await screen.findByText("a.pdf")).toBeTruthy();
    expect(screen.queryByLabelText("Tambah lampiran")).toBeNull();
    expect(screen.queryByRole("button", { name: "Hapus a.pdf" })).toBeNull();
  });
  it("penuh: kolom tambah hilang", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: ["a", "b", "c", "d", "e"].map((i) => item(i)) });
    view();
    expect(await screen.findByText(/sudah penuh/)).toBeTruthy();
    expect(screen.queryByLabelText("Tambah lampiran")).toBeNull();
  });
  it("hapus lewat konfirmasi; milik orang lain tanpa tombol hapus", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [item("a"), item("b", false)] });
    vi.mocked(api.delete).mockResolvedValue({});
    view();
    await screen.findByText("b.pdf");
    expect(screen.queryByRole("button", { name: "Hapus b.pdf" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Hapus a.pdf" }));
    const ok = screen.getAllByRole("button", { name: "Hapus" });
    fireEvent.click(ok[ok.length - 1]);
    await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/overtime/o1/attachments/a"));
  });
  it("unggah lalu tautkan file_id", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    vi.mocked(api.post).mockResolvedValueOnce({ data: { file_id: "f1" } }).mockResolvedValueOnce({ data: [item("f1")] });
    view();
    await screen.findByText("Belum ada lampiran.");
    const file = new File(["x"], "surat.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText("Tambah lampiran"), { target: { files: [file] } });
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/overtime/o1/attachments", { file_id: "f1" }));
    expect(await screen.findByText("f1.pdf")).toBeTruthy();
  });
});
