import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MOCK_PERMISSIONS } from "@/app/mockSession";
import { visibleNav } from "@/app/navigation";
import { PERMISSIONS } from "@/lib/permissions";
import { renderRoute } from "./utils";

const labels = (permissions: readonly string[]) => visibleNav(permissions).map((item) => item.label);

describe("menu berdasarkan izin API", () => {
  it("menampilkan menu hanya ketika izin API yang sesuai tersedia", () => {
    expect(labels([])).toEqual(["Beranda", "Jadwal harian", "Absensi", "Cuti & Izin", "Rekap bulanan", "Kendaraan & alat"]);
    expect(labels(["view:users"])).toEqual(["Beranda", "Jadwal harian", "Absensi", "Cuti & Izin", "Rekap bulanan", "Kendaraan & alat", "Direktori"]);
    // API tidak punya endpoint /users: izin manage:users tidak membuka menu apa pun.
    expect(labels(["manage:users"])).toEqual(["Beranda", "Jadwal harian", "Absensi", "Cuti & Izin", "Rekap bulanan", "Kendaraan & alat"]);
    expect(labels(["view:documents"])).toEqual(["Beranda", "Jadwal harian", "Absensi", "Cuti & Izin", "Rekap bulanan", "Kendaraan & alat", "Berkas saya"]);
    expect(labels(["view:audit"])).toEqual(["Beranda", "Jadwal harian", "Absensi", "Cuti & Izin", "Rekap bulanan", "Kendaraan & alat", "Audit log"]);
    expect(labels(["create:plan"])).toEqual(["Beranda", "Tugas Klien (WO)", "Jadwal harian", "Alokasi mingguan", "Klien", "Absensi", "Cuti & Izin", "Rekap bulanan", "Rekap lembur", "Kendaraan & alat", "Jenis pekerjaan"]);
    // R-33: lokasi kerja dikelola PM (proyek) & Finance (kantor) lewat manage:sites.
    expect(labels(["manage:sites"])).toEqual(["Beranda", "Jadwal harian", "Absensi", "Cuti & Izin", "Rekap bulanan", "Kendaraan & alat", "Lokasi kerja"]);
    expect(labels(["review:overtime"])).toEqual(["Beranda", "Jadwal harian", "Absensi", "Cuti & Izin", "Rekap bulanan", "Rekap lembur", "Kendaraan & alat"]);
  });

  it("izin mock sama dengan peta peran API", () => {
    expect(Object.keys(MOCK_PERMISSIONS).sort()).toEqual(
      ["ADMIN", "ASSET", "FINANCE", "HR", "OPS", "PM", "field"].sort(),
    );
    // R-33: Admin tidak melihat/meninjau absensi orang lain dan tidak mengelola lokasi.
    const adminExcluded = ["view:all_attendance", "review:attendance", "export:attendance", "manage:sites"];
    expect(MOCK_PERMISSIONS.ADMIN).toEqual(PERMISSIONS.filter((p) => !adminExcluded.includes(p)));
    for (const permissions of Object.values(MOCK_PERMISSIONS)) {
      for (const permission of permissions) expect(PERMISSIONS).toContain(permission);
    }
    expect(labels(MOCK_PERMISSIONS.FINANCE)).not.toContain("Audit log");
    expect(labels(MOCK_PERMISSIONS.OPS)).toContain("Audit log");
    expect(labels(MOCK_PERMISSIONS.field)).toEqual(["Beranda", "Jadwal harian", "Absensi", "Cuti & Izin", "Rekap bulanan", "Kendaraan & alat", "Berkas saya", "Direktori"]);
  });

  it("shell memakai permissions[] dari /auth/me untuk menyaring menu", () => {
    renderRoute("/", {
      me: { user_id: "u1", email: "finance@example.com", role: "FINANCE", permissions: ["view:users"] },
    });
    const nav = screen.getByRole("navigation", { name: "Menu utama" });
    expect(nav).toHaveTextContent("Direktori");
    expect(nav).not.toHaveTextContent("Audit log");
  });
});

describe("route guard", () => {
  it("tanpa sesi diarahkan ke login", () => {
    const { router } = renderRoute("/directory");
    expect(router.state.location.pathname).toBe("/login");
  });

  it("izin view:users tidak cukup untuk membuka Audit log", () => {
    const { router } = renderRoute("/audit-logs", {
      me: { user_id: "u1", email: "pm@example.com", role: "PM", permissions: ["view:users"] },
    });
    expect(router.state.location.pathname).toBe("/403");
  });
});
