import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { toast } from "sonner";
import { NAV_ITEMS, isAllowed } from "@/app/navigation";
import type { Me } from "@/lib/types";
import { apiError, mockApi, renderRoute } from "@/test/utils";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const meWith = (permissions: string[]): Me =>
  ({ user_id: "u", email: "x@y.z", role: "X", permissions, employee_id: null }) as unknown as Me;
const ITEM = { id: "t1", module: "tools", name: "Bor Listrik", code: "TL-01", deleted_at: "2026-11-01T00:00:00Z" };

function api(restore?: () => ReturnType<typeof apiError> | { data: unknown }) {
  return mockApi((c) => {
    const m = (c.method ?? "get").toLowerCase();
    if (m === "get" && c.url === "/archive/tools") return { data: [ITEM], headers: { "x-total-count": "1" } };
    if (m === "get" && c.url === "/archive/mess") return { data: [], headers: { "x-total-count": "0" } };
    if (m === "post" && c.url === "/archive/tools/t1/restore") return restore ? restore() : { data: ITEM };
  });
}

describe("Arsip (/archive)", () => {
  it("menu hanya untuk pemegang izin modul yang dicakup", () => {
    const item = NAV_ITEMS.find((i) => i.path === "/archive")!;
    expect(isAllowed(item, ["manage:assets"])).toBe(true);
    expect(isAllowed(item, ["view:users"])).toBe(false);
  });

  it("pilihan modul mengikuti izin dan daftar tampil", async () => {
    api();
    renderRoute("/archive", { me: meWith(["manage:assets"]) });
    expect(await screen.findByText("Bor Listrik")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Kendaraan" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Mess" })).not.toBeInTheDocument();
  });

  it("kosong: menjelaskan tidak ada data terhapus", async () => {
    api();
    renderRoute("/archive", { me: meWith(["manage:mess"]) });
    expect(await screen.findByText("Tidak ada mess yang dihapus.")).toBeInTheDocument();
  });

  it("pulihkan memakai dialog konfirmasi", async () => {
    const calls = api();
    renderRoute("/archive", { me: meWith(["manage:assets"]) });
    fireEvent.click(await screen.findByRole("button", { name: "Pulihkan Bor Listrik" }));
    expect(await screen.findByText("Pulihkan peralatan?")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post")).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Pulihkan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/archive/tools/t1/restore")).toBe(true));
    await waitFor(() => expect(toast.success).toHaveBeenCalled());
  });

  it("konflik 409 menampilkan pesan awam dan dialog tetap terbuka", async () => {
    api(() => apiError(409, "CONFLICT", "Kode peralatan ini sudah dipakai peralatan aktif. Ubah kode peralatan aktif itu dulu."));
    renderRoute("/archive", { me: meWith(["manage:assets"]) });
    fireEvent.click(await screen.findByRole("button", { name: "Pulihkan Bor Listrik" }));
    fireEvent.click(await screen.findByRole("button", { name: "Pulihkan" }));
    expect(await screen.findByText(/sudah dipakai peralatan aktif/)).toBeInTheDocument();
  });
});
