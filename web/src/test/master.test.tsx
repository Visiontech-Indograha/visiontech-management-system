import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { apiError, mockApi, renderRoute } from "./utils";

const page = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 25 });
const product = { id: "p1", code: "CCTV", name: "CCTV", deleted_at: null };

describe("halaman master data", () => {
  it("Admin mengelola produk: daftar, tambah dengan galat server, lalu berhasil", async () => {
    let attempts = 0;
    const calls = mockApi((c) => {
      if (c.url === "/products" && c.method === "get") return { data: page([product]) };
      if (c.url === "/products" && c.method === "post") {
        attempts += 1;
        return attempts === 1
          ? apiError(422, "VALIDATION_ERROR", "x", { fields: { code: "Kode produk sudah dipakai." } })
          : { status: 201, data: { ...product, id: "p2", code: "BARCO", name: "Barco" } };
      }
    });
    renderRoute("/master/products", { role: "admin" });
    expect(await screen.findByText("CCTV", { selector: "span" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Tambah produk" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah produk" });
    fireEvent.change(within(dialog).getByLabelText("Kode"), { target: { value: "cctv" } });
    fireEvent.change(within(dialog).getByLabelText("Nama"), { target: { value: "Kamera" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Kode produk sudah dipakai.")).toBeInTheDocument();
    // isian tidak hilang saat galat
    expect(within(dialog).getByLabelText("Nama")).toHaveValue("Kamera");

    fireEvent.change(within(dialog).getByLabelText("Kode"), { target: { value: "BARCO" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const posts = calls.filter((c) => c.method === "post");
    expect(posts[1].data).toMatchObject({ code: "BARCO", name: "Kamera" });
  });

  it("ubah dan hapus memanggil PATCH dan DELETE pada id yang benar", async () => {
    const calls = mockApi((c) => {
      if (c.method === "get") return { data: page([product]) };
      if (c.method === "patch") return { data: { ...product, name: "Kamera CCTV" } };
      if (c.method === "delete") return { status: 204, data: null };
    });
    renderRoute("/master/products", { role: "admin" });
    fireEvent.click(await screen.findByRole("button", { name: "Ubah" }));
    const dialog = screen.getByRole("dialog", { name: "Ubah produk" });
    expect(within(dialog).getByLabelText("Kode")).toHaveValue("CCTV");
    fireEvent.change(within(dialog).getByLabelText("Nama"), { target: { value: "Kamera CCTV" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "patch")).toBe(true));
    expect(calls.find((c) => c.method === "patch")).toMatchObject({ url: "/products/p1" });

    fireEvent.click(await screen.findByRole("button", { name: "Hapus" }));
    const confirm = await screen.findByRole("dialog", { name: "Hapus CCTV?" });
    fireEvent.click(within(confirm).getByRole("button", { name: "Hapus" }));
    await waitFor(() => expect(calls.some((c) => c.method === "delete")).toBe(true));
    expect(calls.find((c) => c.method === "delete")).toMatchObject({ url: "/products/p1" });
  });

  it("role hanya-baca tidak melihat tombol tambah/ubah/hapus", async () => {
    mockApi((c) => (c.method === "get" ? { data: page([product]) } : undefined));
    const base = mockMe("admin")!;
    const readOnly = { ...base, manage_permissions: base.manage_permissions.filter((p) => p !== "master:product") };
    renderRoute("/master/products", { me: readOnly });
    expect(await screen.findByText("CCTV", { selector: "span" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tambah produk" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Ubah" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Hapus" })).toBeNull();
  });

  it("keadaan kosong menawarkan aksi tambah", async () => {
    mockApi((c) => (c.method === "get" ? { data: page([]) } : undefined));
    renderRoute("/master/vehicles", { role: "admin" });
    expect(await screen.findByText(/Belum ada kendaraan/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Tambah kendaraan" })).toHaveLength(2);
  });

  it("halaman item tool/APD: berganti kategori dan mengirim kategori saat membuat", async () => {
    const calls = mockApi((c) => {
      if (c.method === "get") return { data: page([]) };
      if (c.method === "post") return { status: 201, data: { id: "i1" } };
    });
    renderRoute("/master/items-tool", { role: "hes" });
    await screen.findByText(/Belum ada tool/);
    expect(calls[0].url).toBe("/items");

    fireEvent.click(screen.getByRole("button", { name: "APD" }));
    await screen.findByText(/Belum ada APD/);
    fireEvent.click(screen.getAllByRole("button", { name: "Tambah APD" })[0]);
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Nama"), { target: { value: "Helm" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post")).toBe(true));
    expect(calls.find((c) => c.method === "post")!.data).toMatchObject({
      category: "PPE",
      name: "Helm",
      returnable: false,
    });
  });

  it("Admin tidak dapat membuka halaman item tool/APD; HES tidak dapat membuka item barang", () => {
    mockApi(() => undefined);
    expect(renderRoute("/master/items-tool", { role: "admin" }).router.state.location.pathname).toBe("/forbidden");
    expect(renderRoute("/master/items-project", { role: "hes" }).router.state.location.pathname).toBe("/forbidden");
  });
});
