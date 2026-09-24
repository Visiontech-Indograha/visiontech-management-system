import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MOCK_PERMISSIONS } from "@/app/mockSession";
import { visibleNav } from "@/app/navigation";
import { PERMISSIONS } from "@/lib/permissions";
import { renderRoute } from "./utils";

const labels = (permissions: readonly string[]) => visibleNav(permissions).map((item) => item.label);

describe("menu berdasarkan izin API", () => {
  it("menampilkan menu hanya ketika izin API yang sesuai tersedia", () => {
    expect(labels([])).toEqual(["Beranda"]);
    expect(labels(["view:users"])).toEqual(["Beranda", "Direktori"]);
    expect(labels(["manage:users"])).toEqual(["Beranda", "Pengguna"]);
    expect(labels(["view:documents"])).toEqual(["Beranda", "Berkas saya"]);
    expect(labels(["view:audit"])).toEqual(["Beranda", "Audit log"]);
  });

  it("izin mock sama dengan peta peran API", () => {
    expect(Object.keys(MOCK_PERMISSIONS).sort()).toEqual(
      ["ADMIN", "ASSET", "FINANCE", "HR", "OPS", "PM", "field"].sort(),
    );
    expect(MOCK_PERMISSIONS.ADMIN).toEqual([...PERMISSIONS]);
    for (const permissions of Object.values(MOCK_PERMISSIONS)) {
      for (const permission of permissions) expect(PERMISSIONS).toContain(permission);
    }
    expect(labels(MOCK_PERMISSIONS.FINANCE)).not.toContain("Pengguna");
    expect(labels(MOCK_PERMISSIONS.HR)).toContain("Pengguna");
    expect(labels(MOCK_PERMISSIONS.field)).toEqual(["Beranda", "Direktori", "Berkas saya"]);
  });

  it("shell memakai permissions[] dari /auth/me untuk menyaring menu", () => {
    renderRoute("/", {
      me: { user_id: "u1", email: "finance@example.com", role: "FINANCE", permissions: ["view:users"] },
    });
    const nav = screen.getByRole("navigation", { name: "Menu utama" });
    expect(nav).toHaveTextContent("Direktori");
    expect(nav).not.toHaveTextContent("Pengguna");
    expect(nav).not.toHaveTextContent("Audit log");
  });
});

describe("route guard", () => {
  it("tanpa sesi diarahkan ke login", () => {
    const { router } = renderRoute("/directory");
    expect(router.state.location.pathname).toBe("/login");
  });

  it("izin view:users tidak cukup untuk membuka halaman Pengguna", () => {
    const { router } = renderRoute("/users", {
      me: { user_id: "u1", email: "pm@example.com", role: "PM", permissions: ["view:users"] },
    });
    expect(router.state.location.pathname).toBe("/forbidden");
  });
});
