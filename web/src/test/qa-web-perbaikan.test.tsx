import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { assetRowActions } from "@/lib/aksiPeran";
import { roleScopeLines } from "@/lib/roleAssignments";
import { safeRedirectPath } from "@/lib/safeRedirect";
import { loginSchema } from "@/schemas/loginSchema";
import type { Me } from "@/lib/types";
import { mockApi, renderRoute } from "./utils";

const meDengan = (permissions: string[]): Me =>
  ({ user_id: "u", email: "x@example.com", role: "ADMIN_HR_GA", permissions, employee_id: null }) as unknown as Me;
const tim = { team_id: "t1", name: "Tim Alpha", member_count: 2, division_name: "Sipil", office_name: "Pusat", leader_name: "Agus" };
const pegawai = {
  employee_id: "e1", employee_no: "K-1", full_name: "Budi", join_date: "2024-01-01",
  position_name: null, division_name: null, office_name: "Kantor Pekanbaru", status: "active",
};

describe("perbaikan QA web", () => {
  it("email kosong: Email wajib diisi", () => {
    const r = loginSchema.safeParse({ email: "", password: "x" });
    expect(r.success).toBe(false);
    if (!r.success) expect(r.error.issues[0].message).toBe("Email wajib diisi.");
  });
  it("tujuan setelah login hanya jalur internal", () => {
    expect(safeRedirectPath("/attendance?x=1")).toBe("/attendance?x=1");
    for (const bad of ["//evil.com", "https://evil.com", "/\\evil.com", "javascript:1", undefined, "/login"])
      expect(safeRedirectPath(bad)).toBe("/");
  });
  it("peran utama tidak diulang di baris cakupan", () => {
    const sc = (role: string) => ({ role, office_id: null, office_name: null });
    expect(roleScopeLines({ role: "EMPLOYEE", role_scopes: [sc("EMPLOYEE")] } as never)).toEqual([]);
    expect(roleScopeLines({ role: "EMPLOYEE", role_scopes: [sc("FINANCE")] } as never)).toEqual(["Finance"]);
  });
  it("aset: tanpa manage:assets tidak ada tombol tulis", () => {
    expect(assetRowActions(false, "TOOL", "ready", false)).toEqual([]);
    expect(assetRowActions(false, "VEHICLE", "ready", false)).toEqual(["files"]);
  });

  it("Tambah Tim dan Hapus tersembunyi tanpa manage:teams", async () => {
    mockApi((c) => (c.url === "/teams" ? { data: [tim] } : undefined));
    renderRoute("/teams", { me: meDengan(["view:teams"]) });
    expect(await screen.findByText("Tim Alpha")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tambah Tim" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Hapus Tim Alpha" })).toBeNull();
  });
  it("Tambah Tim tampil dengan manage:teams", async () => {
    mockApi((c) => (c.url === "/teams" ? { data: [tim] } : undefined));
    renderRoute("/teams", { me: meDengan(["view:teams", "manage:teams"]) });
    expect(await screen.findByRole("button", { name: "Tambah Tim" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Hapus Tim Alpha" })).toBeInTheDocument();
  });
  it("kolom Jabatan tidak menampilkan nama kantor", async () => {
    mockApi((c) => (c.url === "/employees" ? { data: { items: [pegawai], total: 1, page: 1, size: 20 } } : undefined));
    renderRoute("/directory", { me: meDengan(["view:users", "manage:users"]) });
    expect(await screen.findAllByText("Budi")).not.toHaveLength(0);
    expect(screen.queryByText(/Kantor Pekanbaru/)).toBeNull();
  });
});
