import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FilePreview } from "./FilePreview";
import { api, ApiError } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", () => ({
  api: { get: vi.fn() },
  ApiError: class extends Error {
    status: number;
    code: string;
    constructor(code: string, message: string, status: number) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("FilePreview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("open", vi.fn());
  });

  it("menampilkan Skeleton saat memuat", () => {
    vi.mocked(api.get).mockImplementation(() => new Promise(() => {}));
    renderWithClient(<FilePreview fileId="f1" fileName="Test Doc" />);
    expect(screen.getByTestId("file-preview-skeleton")).toBeInTheDocument();
  });

  it("menampilkan unduh jika mime_type bukan gambar, dan fetch ulang saat diklik", async () => {
    // Awalnya render dengan data awal
    vi.mocked(api.get).mockResolvedValueOnce({ data: { url: "https://mock/file.pdf", mime_type: "application/pdf" } });
    renderWithClient(<FilePreview fileId="f2" fileName="Sertifikat" />);
    
    const btn = await screen.findByRole("button", { name: /Unduh Sertifikat/i });
    expect(btn).toBeInTheDocument();
    
    // Saat diklik, ambil URL full
    vi.mocked(api.get).mockResolvedValueOnce({ data: { url: "https://mock/file_full.pdf", mime_type: "application/pdf" } });
    fireEvent.click(btn);
    
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/files/f2/url?variant=full");
      expect(window.open).toHaveBeenCalledWith("https://mock/file_full.pdf", "_blank");
    });
  });

  it("menampilkan gambar jika mime_type gambar (200 Image)", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { url: "https://mock/file.webp", mime_type: "image/webp" } });
    renderWithClient(<FilePreview fileId="f3" fileName="KTP" />);
    
    const img = await screen.findByRole("img", { name: "KTP" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://mock/file.webp");
  });

  it("menampilkan pesan 'Berkas tidak tersedia' jika 404", async () => {
    vi.mocked(api.get).mockRejectedValue(new ApiError("NOT_FOUND", "Berkas tidak ditemukan.", 404));
    renderWithClient(<FilePreview fileId="f4" />);
    
    expect(await screen.findByText("Berkas tidak tersedia")).toBeInTheDocument();
  });

  it("menampilkan galat jaringan dan tombol coba lagi, lalu berhasil", async () => {
    vi.mocked(api.get)
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce({ data: { url: "https://mock/file.webp", mime_type: "image/webp" } });
      
    renderWithClient(<FilePreview fileId="f5" fileName="Pasfoto" />);
    
    expect(await screen.findByText("Gagal memuat")).toBeInTheDocument();
    const btn = screen.getByRole("button", { name: "Coba lagi" });
    
    fireEvent.click(btn);
    const img = await screen.findByRole("img", { name: "Pasfoto" });
    expect(img).toBeInTheDocument();
  });

  it("melakukan refetch jika url gambar kedaluwarsa (onError)", async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { url: "https://mock/expired.webp", mime_type: "image/webp" } })
      .mockResolvedValueOnce({ data: { url: "https://mock/new.webp", mime_type: "image/webp" } });
      
    renderWithClient(<FilePreview fileId="f6" fileName="SIM" />);
    
    const img = await screen.findByRole("img", { name: "SIM" });
    expect(img).toHaveAttribute("src", "https://mock/expired.webp");

    // Simulasi gambar gagal dimuat (URL expired)
    fireEvent.error(img);

    await waitFor(() => {
      expect(screen.getByRole("img", { name: "SIM" })).toHaveAttribute("src", "https://mock/new.webp");
    });
    
    expect(api.get).toHaveBeenCalledTimes(2);
  });
});
