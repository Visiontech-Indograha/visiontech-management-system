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
    expect(router.state.location.pathname).toBe("/403");
  });

  it("menampilkan daftar dan keadaan kosong", async () => {
    mockApi((c) => (c.url === "/offices" ? { data: [site] } : undefined));
    renderRoute("/sites", { role: "PM" });
    expect(await screen.findByText("Gudang Cikarang")).toBeInTheDocument();
    expect(screen.getByText(/radius 50 m/)).toBeInTheDocument();
  });

  it("menambah lokasi mengirim SiteCreate", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/offices" && c.method === "get") return { data: [] };
      if (c.url === "/offices" && c.method === "post") return { status: 201, data: site };
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
    const calls = mockApi((c) => (c.url === "/offices" ? { data: [] } : undefined));
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
      if (c.url === "/offices") return { data: [{ ...site, can_manage: true }] };
      if (c.url === "/offices/s1" && c.method === "delete") return { data: { message: "Lokasi dihapus." } };
    });
    renderRoute("/sites", { role: "PM" });
    fireEvent.click(await screen.findByRole("button", { name: "Hapus Gudang Cikarang" }));
    const dialog = screen.getByRole("dialog", { name: "Hapus lokasi kerja" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Hapus" }));
    await waitFor(() => expect(calls.some((c) => c.method === "delete" && c.url === "/offices/s1")).toBe(true));
  });

  it("galat memuat menampilkan Coba lagi", async () => {
    mockApi(() => apiError(500, "INTERNAL_ERROR", "Terjadi gangguan pada sistem. Coba lagi beberapa saat; bila berulang, hubungi admin."));
    renderRoute("/sites", { role: "PM" });
    expect(await screen.findByRole("button", { name: "Coba lagi" })).toBeInTheDocument();
  });

  it("dialog tambah punya peta dinamis dan pencarian alamat; hasil cari mengisi lintang, bujur, dan alamat", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/offices") return { data: [] };
      if (c.url === "/work-plans/geo/search") return { data: [{ name: "Jl. Sudirman, Pekanbaru, Riau", type: "road", lat: 0.5071, lng: 101.4478 }] };
    });
    renderRoute("/sites", { role: "PM" });
    await screen.findByText(/Belum ada lokasi kerja/);
    fireEvent.click(screen.getAllByRole("button", { name: "Tambah lokasi" })[0]);
    const dialog = screen.getByRole("dialog", { name: "Tambah lokasi kerja" });
    expect(within(dialog).getByTestId("site-map")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Cari alamat atau nama tempat"), { target: { value: "sudirman pekanbaru" } });
    fireEvent.click(await within(dialog).findByText("Jl. Sudirman, Pekanbaru, Riau", {}, { timeout: 4000 }));
    expect(within(dialog).getByLabelText("Lintang (lat)")).toHaveValue("0.507100");
    expect(within(dialog).getByLabelText("Bujur (lng)")).toHaveValue("101.447800");
    expect(within(dialog).getByLabelText("Alamat")).toHaveValue("Jl. Sudirman, Pekanbaru, Riau");
    expect(within(dialog).getByLabelText("Nama lokasi")).toHaveValue("Jl. Sudirman");
    expect(calls.some((c) => c.url === "/work-plans/geo/search")).toBe(true);
  });

  it("lintang/bujur tetap bisa diketik manual dan penanda mengikuti", async () => {
    mockApi((c) => (c.url === "/offices" ? { data: [] } : undefined));
    renderRoute("/sites", { role: "PM" });
    await screen.findByText(/Belum ada lokasi kerja/);
    fireEvent.click(screen.getAllByRole("button", { name: "Tambah lokasi" })[0]);
    const dialog = screen.getByRole("dialog", { name: "Tambah lokasi kerja" });
    fireEvent.change(within(dialog).getByLabelText("Lintang (lat)"), { target: { value: "0.5" } });
    fireEvent.change(within(dialog).getByLabelText("Bujur (lng)"), { target: { value: "101.4" } });
    await waitFor(() => expect(dialog.querySelector(".leaflet-marker-icon")).not.toBeNull());
  });
});
