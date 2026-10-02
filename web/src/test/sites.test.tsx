import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const site = {
  id: "s1",
  name: "Gudang Cikarang",
  address: "Jl. Industri 1",
  location: { lat: -6.3, lng: 107.15 },
  radius_m: 50,
};

describe("Lokasi kerja (/sites)", () => {
  it("tanpa manage:sites ditolak", () => {
    mockApi(() => undefined);
    const { router } = renderRoute("/sites", { role: "HR" });
    expect(router.state.location.pathname).toBe("/forbidden");
  });

  it("menampilkan daftar dan keadaan kosong", async () => {
    mockApi((c) => (c.url === "/sites" ? { data: [site] } : undefined));
    renderRoute("/sites", { role: "PM" });
    expect(await screen.findByText("Gudang Cikarang")).toBeInTheDocument();
    expect(screen.getByText(/radius 50 m/)).toBeInTheDocument();
  });

  it("menambah lokasi mengirim SiteCreate", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/sites" && c.method === "get") return { data: [] };
      if (c.url === "/sites" && c.method === "post") return { status: 201, data: site };
    });
    renderRoute("/sites", { role: "PM" });
    await screen.findByText(/Belum ada lokasi kerja/);
    fireEvent.click(screen.getAllByRole("button", { name: "Tambah lokasi" })[0]);
    const dialog = screen.getByRole("dialog", { name: "Tambah lokasi kerja" });
    fireEvent.change(within(dialog).getByLabelText("Nama lokasi"), { target: { value: "Gudang Cikarang" } });
    fireEvent.change(within(dialog).getByLabelText("Lintang (lat)"), { target: { value: "-6.3" } });
    fireEvent.change(within(dialog).getByLabelText("Bujur (lng)"), { target: { value: "107.15" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post")).toBe(true));
    expect(calls.find((c) => c.method === "post")!.data).toEqual({
      name: "Gudang Cikarang",
      address: null,
      location: { lat: -6.3, lng: 107.15 },
      radius_m: 50,
    });
  });

  it("validasi: lintang di luar rentang tidak dikirim", async () => {
    const calls = mockApi((c) => (c.url === "/sites" ? { data: [] } : undefined));
    renderRoute("/sites", { role: "PM" });
    await screen.findByText(/Belum ada lokasi kerja/);
    fireEvent.click(screen.getAllByRole("button", { name: "Tambah lokasi" })[0]);
    const dialog = screen.getByRole("dialog", { name: "Tambah lokasi kerja" });
    fireEvent.change(within(dialog).getByLabelText("Nama lokasi"), { target: { value: "X" } });
    fireEvent.change(within(dialog).getByLabelText("Lintang (lat)"), { target: { value: "95" } });
    fireEvent.change(within(dialog).getByLabelText("Bujur (lng)"), { target: { value: "10" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByText("Lintang harus angka antara -90 dan 90.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post")).toBe(false);
  });

  it("menghapus lewat dialog konfirmasi", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/sites") return { data: [{ ...site, can_manage: true }] };
      if (c.url === "/sites/s1" && c.method === "delete") return { data: { message: "Lokasi dihapus." } };
    });
    renderRoute("/sites", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Hapus Gudang Cikarang" }));
    const dialog = screen.getByRole("dialog", { name: "Hapus lokasi kerja" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Hapus" }));
    await waitFor(() => expect(calls.some((c) => c.method === "delete" && c.url === "/sites/s1")).toBe(true));
  });

  it("galat memuat menampilkan Coba lagi", async () => {
    mockApi(() => apiError(500, "INTERNAL_ERROR", "Terjadi kesalahan internal pada server."));
    renderRoute("/sites", { role: "PM" });
    expect(await screen.findByRole("button", { name: "Coba lagi" })).toBeInTheDocument();
  });
});
