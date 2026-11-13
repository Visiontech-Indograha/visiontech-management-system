import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { ClientSitesModal } from "./ClientSitesModal";
import { mockApi, apiError } from "@/test/utils";
import type { Client, ClientSite } from "@/services/clientService";

const mockClient: Client = {
  client_id: "c-100",
  client_code: "CL-01",
  name: "PT Telko Pratama",
  pic_name: "Budi",
  pic_phone: "08123456789",
  address: "Jl. Sudirman",
  status: true,
  project_count: 2,
};

const mockSite: ClientSite = {
  site_id: "s-01",
  client_id: "c-100",
  site_name: "Gudang Cikarang",
  address: "Kawasan Industri MM2100",
  latitude: -6.301,
  longitude: 107.123,
  geofence_radius_meters: 150,
  pic_name: "Andi",
  pic_phone: "0811223344",
};

function renderModal(onClose = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <ClientSitesModal client={mockClient} onClose={onClose} />
    </QueryClientProvider>,
  );
  return { onClose };
}

describe("ClientSitesModal - Konfirmasi Hapus Lokasi Cabang (U-01)", () => {
  it("klik tombol Hapus membuka ConfirmDialog dengan nama objek dan akibatnya", async () => {
    mockApi((c) => {
      if (c.url === "/clients/c-100/sites" && c.method === "get") return { data: [mockSite] };
    });

    renderModal();

    expect(await screen.findByText("Gudang Cikarang")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Hapus lokasi Gudang Cikarang" }));

    const dialog = await screen.findByRole("dialog", { name: "Hapus lokasi cabang" });
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText(/Hapus lokasi Gudang Cikarang\? Absensi di lokasi ini tidak bisa memakainya lagi\./)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Hapus" })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Batal" })).toBeInTheDocument();
  });

  it("klik Batal menutup ConfirmDialog tanpa memanggil API delete", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/clients/c-100/sites" && c.method === "get") return { data: [mockSite] };
    });

    renderModal();

    expect(await screen.findByText("Gudang Cikarang")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Hapus lokasi Gudang Cikarang" }));

    const dialog = await screen.findByRole("dialog", { name: "Hapus lokasi cabang" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Batal" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Hapus lokasi cabang" })).toBeNull();
    });
    expect(calls.some((c) => c.method === "delete")).toBe(false);
  });

  it("konfirmasi Hapus memanggil API delete dan menutup konfirmasi setelah sukses", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/clients/c-100/sites" && c.method === "get") return { data: [mockSite] };
      if (c.url === "/clients/c-100/sites/s-01" && c.method === "delete") {
        return { status: 200, data: { message: "Lokasi berhasil dihapus." } };
      }
    });

    renderModal();

    expect(await screen.findByText("Gudang Cikarang")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Hapus lokasi Gudang Cikarang" }));

    const dialog = await screen.findByRole("dialog", { name: "Hapus lokasi cabang" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Hapus" }));

    await waitFor(() => {
      expect(calls.some((c) => c.method === "delete" && c.url === "/clients/c-100/sites/s-01")).toBe(true);
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Hapus lokasi cabang" })).toBeNull();
    });
  });

  it("galat server menampilkan pesan errorMessage", async () => {
    mockApi((c) => {
      if (c.url === "/clients/c-100/sites" && c.method === "get") return { data: [mockSite] };
      if (c.url === "/clients/c-100/sites/s-01" && c.method === "delete") {
        return apiError(409, "SITE_IN_USE", "Lokasi cabang masih digunakan dalam riwayat absensi atau tugas kerja aktif.");
      }
    });

    renderModal();

    expect(await screen.findByText("Gudang Cikarang")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Hapus lokasi Gudang Cikarang" }));

    const dialog = await screen.findByRole("dialog", { name: "Hapus lokasi cabang" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Hapus" }));

    expect(await within(dialog).findByText("Lokasi cabang masih digunakan dalam riwayat absensi atau tugas kerja aktif.")).toBeInTheDocument();
  });
});
