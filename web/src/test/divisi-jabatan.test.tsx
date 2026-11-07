import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { toast } from "sonner";
import { NAV_ITEMS, isAllowed } from "@/app/navigation";
import type { Me } from "@/lib/types";
import { apiError, mockApi, renderRoute } from "./utils";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const DIV = { id: "d1", code: "FTTX", name: "Fiber Optik", status: true, om_id: "e1", pm_id: "e2", om_name: "Budi OM", pm_name: "Sari PM", team_count: 2 };
const POS = { position_id: "p1", division_id: "d1", code: "TKN", name: "Teknisi", grade_level: 3, daily_allowance: "0", status: true, employee_count: 4 };
const PEOPLE = [{ employee_id: "e1", employee_no: "K1", full_name: "Budi OM" }, { employee_id: "e2", employee_no: "K2", full_name: "Sari PM" }];

const meWith = (permissions: string[]): Me =>
  ({ user_id: "u", email: "x@y.z", role: "X", permissions, employee_id: null }) as unknown as Me;

function api(extra?: Parameters<typeof mockApi>[0]) {
  return mockApi((c) => {
    const r = extra?.(c);
    if (r) return r;
    const m = (c.method ?? "get").toLowerCase();
    if (m !== "get") return undefined;
    if (c.url === "/divisions") return { data: [DIV] };
    if (c.url === "/job-positions") return { data: [POS] };
    if (c.url === "/employees") return { data: { items: PEOPLE, total: 2 } };
  });
}

describe("Divisi dan jabatan (/divisions)", () => {
  it("menu hanya untuk yang punya izin kelola divisi atau jabatan", () => {
    const item = NAV_ITEMS.find((i) => i.path === "/divisions")!;
    expect(isAllowed(item, ["manage:divisions"])).toBe(true);
    expect(isAllowed(item, ["manage:users"])).toBe(true);
    expect(isAllowed(item, ["view:users"])).toBe(false);
  });

  it("menampilkan divisi dengan jabatannya dan tombol sesuai izin", async () => {
    api();
    renderRoute("/divisions", { me: meWith(["manage:divisions"]) });
    expect(await screen.findByText("Fiber Optik (FTTX)")).toBeInTheDocument();
    expect(screen.getByText("Teknisi (TKN)")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Tambah divisi" }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Tambah jabatan" })).not.toBeInTheDocument();
  });

  it("HR hanya mengelola jabatan, bukan divisi", async () => {
    api();
    renderRoute("/divisions", { role: "HR" });
    await screen.findByText("Teknisi (TKN)");
    expect(screen.getByRole("button", { name: "Tambah jabatan" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tambah divisi" })).not.toBeInTheDocument();
  });

  it("pencarian memakai awalan nama", async () => {
    api();
    renderRoute("/divisions", { role: "ADMIN" });
    await screen.findByText("Fiber Optik (FTTX)");
    fireEvent.change(screen.getByLabelText("Cari"), { target: { value: "ptik" } });
    expect(await screen.findByText("Tidak ada divisi atau jabatan yang cocok.")).toBeInTheDocument();
  });

  it("tambah divisi: kirim nama, OM, dan PM", async () => {
    const calls = api();
    renderRoute("/divisions", { role: "ADMIN" });
    await screen.findByText("Fiber Optik (FTTX)");
    fireEvent.click(screen.getAllByRole("button", { name: "Tambah divisi" })[0]);
    const dialog = await screen.findByRole("dialog", { name: "Tambah divisi" });
    await within(dialog).findAllByRole("option", { name: "Budi OM (K1)" });
    fireEvent.change(within(dialog).getByLabelText("Nama divisi"), { target: { value: "Jaringan" } });
    fireEvent.change(within(dialog).getByLabelText("Operational Manager (OM)"), { target: { value: "e1" } });
    fireEvent.change(within(dialog).getByLabelText("Project Manager (PM)"), { target: { value: "e2" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.find((c) => c.method === "post")?.data).toEqual({ name: "Jaringan", om_id: "e1", pm_id: "e2" }));
  });

  it("tambah jabatan: batas tingkat 1 sampai 20 dijaga", async () => {
    const calls = api();
    renderRoute("/divisions", { role: "HR" });
    await screen.findByText("Teknisi (TKN)");
    fireEvent.click(screen.getAllByRole("button", { name: "Tambah jabatan" })[0]);
    const dialog = await screen.findByRole("dialog", { name: "Tambah jabatan" });
    fireEvent.change(within(dialog).getByLabelText("Kode jabatan"), { target: { value: "SPV" } });
    fireEvent.change(within(dialog).getByLabelText("Nama jabatan"), { target: { value: "Supervisor" } });
    fireEvent.change(within(dialog).getByLabelText("Tingkat"), { target: { value: "25" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByText("Tingkat maksimal 20.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post")).toBe(false);
  });

  it("hapus divisi minta konfirmasi dan pesan galat awam bila masih dipakai", async () => {
    const calls = api((c) =>
      c.method === "delete" ? apiError(409, "DIVISION_IN_USE", "Divisi masih dipakai 2 tim dan 4 karyawan aktif.") : undefined,
    );
    renderRoute("/divisions", { role: "ADMIN" });
    await screen.findByText("Fiber Optik (FTTX)");
    expect(calls.some((c) => c.method === "delete")).toBe(false);
    fireEvent.click(screen.getAllByRole("button", { name: "Hapus" })[0]);
    const dialog = await screen.findByRole("dialog", { name: "Hapus divisi?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Hapus" }));
    await waitFor(() => expect(calls.some((c) => c.method === "delete" && c.url === "/divisions/d1")).toBe(true));
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Divisi masih dipakai 2 tim dan 4 karyawan aktif."));
  });
});
