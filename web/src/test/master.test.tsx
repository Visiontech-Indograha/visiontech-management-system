import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const page = (items: unknown[]) => ({ items, total: items.length, page: 1, size: 25 });
const site = { id: "s1", name: "Site A", customer_name: "Customer A", address: "Jakarta", deleted_at: null };

describe("halaman master data", () => {
  it("Super Admin mengelola site: daftar, tambah dengan galat server, lalu berhasil", async () => {
    let attempts = 0;
    const calls = mockApi((c) => {
      if (c.url === "/sites" && c.method === "get") return { data: page([site]) };
      if (c.url === "/sites" && c.method === "post") {
        attempts += 1;
        return attempts === 1
          ? apiError(422, "VALIDATION_ERROR", "x", { fields: { name: "Nama site sudah dipakai." } })
          : { status: 201, data: { ...site, id: "s2", name: "Site B" } };
      }
    });
    renderRoute("/master/sites", { role: "super_admin" });
    expect(await screen.findByText("Site A", { selector: "span" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Tambah site" }));
    const dialog = screen.getByRole("dialog", { name: "Tambah site" });
    fireEvent.change(within(dialog).getByLabelText("Nama"), { target: { value: "Site B" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Nama site sudah dipakai.")).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText("Nama"), { target: { value: "Site C" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(calls.filter((c) => c.method === "post").length).toBe(2);
  });

  it("ubah dan hapus memanggil PATCH dan DELETE pada id yang benar", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/sites" && c.method === "get") return { data: page([site]) };
      if (c.url === "/sites/s1") return { data: site }; // patch/delete response
    });
    renderRoute("/master/sites", { role: "super_admin" });
    const row = await screen.findByRole("row", { name: /Site A/ });

    fireEvent.click(within(row).getByRole("button", { name: "Ubah" }));
    const dialog = screen.getByRole("dialog", { name: "Ubah site" });
    fireEvent.change(within(dialog).getByLabelText("Nama"), { target: { value: "Site X" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "patch" && c.url === "/sites/s1")).toBe(true));

    fireEvent.click(within(row).getByRole("button", { name: "Hapus" }));
    const deleteDialog = screen.getByRole("dialog");
    fireEvent.click(within(deleteDialog).getByRole("button", { name: "Hapus" }));
    await waitFor(() => expect(calls.some((c) => c.method === "delete" && c.url === "/sites/s1")).toBe(true));
  });

  it("keadaan kosong menawarkan aksi tambah", async () => {
    mockApi((c) => (c.url === "/sites" ? { data: page([]) } : undefined));
    renderRoute("/master/sites", { role: "super_admin" });
    expect(await screen.findByRole("button", { name: "Tambah site" })).toBeInTheDocument();
  });
});
