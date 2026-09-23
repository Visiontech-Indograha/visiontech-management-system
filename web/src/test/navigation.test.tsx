import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MOCK_PERMISSIONS } from "@/app/mockSession";
import { visibleNav } from "@/app/navigation";
import { PERMISSIONS } from "@/lib/permissions";
import { renderRoute } from "./utils";

const labels = (role: string) => visibleNav(MOCK_PERMISSIONS[role]).map((i) => i.label);

// Inventaris menu web: docs/06-UI-UX §5
const EXPECTED: Record<string, string[]> = {
  super_admin: [
    "Beranda", "Pengguna", "Direktori", "Absensi", "Produk", "Kendaraan", "Item barang",
    "Item tool/APD", "Jenis berkas", "Site", "Audit log",
  ],
  admin: ["Beranda", "Direktori", "Serah terima barang", "Status kendaraan", "Produk", "Kendaraan", "Item barang"],
  team_leader: [
    "Beranda", "Direktori", "Team", "Work plan", "Progress", "Persetujuan kendaraan", "Laporan",
    "Absensi team", "Site",
  ],
  finance: ["Beranda", "Direktori", "Absensi"],
  hes: ["Beranda", "Direktori", "Perlu dilengkapi", "Serah terima tool/APD", "Item tool/APD", "Jenis berkas"],
  wtl: ["Beranda", "Plan saya", "Progress", "Barang saya", "Berkas saya"],
  driver: ["Beranda", "Logbook kendaraan", "Plan team", "Barang saya", "Berkas saya"],
};

describe("menu per role", () => {
  for (const [role, expected] of Object.entries(EXPECTED)) {
    it(`${role} melihat menu sesuai docs`, () => {
      expect([...labels(role)].sort()).toEqual([...expected].sort());
    });
  }

  it("Finance, Admin, dan HES tidak melihat menu work plan (BR-17)", () => {
    for (const role of ["finance", "admin", "hes"]) {
      const l = labels(role);
      expect(l).not.toContain("Work plan");
      expect(l).not.toContain("Plan saya");
      expect(l).not.toContain("Plan team");
    }
  });

  it("semua permission mock dikenal (tidak ada salah ketik)", () => {
    const known = new Set<string>(PERMISSIONS);
    for (const perms of Object.values(MOCK_PERMISSIONS)) {
      for (const p of perms) expect(known.has(p)).toBe(true);
    }
  });
});

function renderAt(path: string, role: string | null) {
  return renderRoute(path, { role }).router;
}

describe("route guard", () => {
  it("tanpa sesi diarahkan ke /login", () => {
    const router = renderAt("/work-plans", null);
    expect(router.state.location.pathname).toBe("/login");
  });

  it("Finance membuka /work-plans → /forbidden", () => {
    const router = renderAt("/work-plans", "finance");
    expect(router.state.location.pathname).toBe("/forbidden");
    expect(screen.getByText("Akses ditolak")).toBeInTheDocument();
  });

  it("TL dapat membuka /work-plans", () => {
    const router = renderAt("/work-plans", "team_leader");
    expect(router.state.location.pathname).toBe("/work-plans");
    expect(screen.getByRole("heading", { name: "Work plan" })).toBeInTheDocument();
  });

  it("shell menampilkan menu sesuai role", () => {
    renderAt("/", "wtl");
    const nav = screen.getByRole("navigation", { name: "Menu utama" });
    expect(nav).toHaveTextContent("Plan saya");
    expect(nav).not.toHaveTextContent("Direktori");
  });
});
