/**
 * Matriks peran × status untuk tombol Jenis pekerjaan, Aset (kendaraan & alat), dan Mess.
 * Izin tiap peran mengikuti docs/diagram/00-peran-dan-izin.md §2, ditulis sebagai nama permission web.
 * Harapan di tabel ditulis tangan dari aturan, bukan dihitung ulang dari helper.
 */
import { describe, expect, it } from "vitest";
import { assetRowActions, canManageAssets, messActions, workTypeActions } from "@/lib/aksiPeran";

const PERAN = {
  SUPER_ADMIN: ["create:plan", "manage:assets", "manage:mess", "view:mess", "review:mess"],
  ADMIN: ["create:plan", "manage:assets", "manage:mess", "view:mess", "review:mess"],
  OM: ["create:plan", "view:mess", "review:mess"],
  PM: ["create:plan", "view:mess", "review:mess"],
  HR: ["manage:assets", "manage:mess", "view:mess", "review:mess"],
  ASSET: ["manage:assets"],
  FINANCE: ["review:overtime", "export:attendance"],
  KETUA: [],
  ANGGOTA: [],
} as const;
type Peran = keyof typeof PERAN;

describe("Jenis pekerjaan: peran × status (aktif / nonaktif)", () => {
  const expected: Record<Peran, [string[], string[]]> = {
    // [aktif, nonaktif]
    SUPER_ADMIN: [["edit", "materials", "copy", "deactivate"], ["edit", "materials"]],
    ADMIN: [["edit", "materials", "copy", "deactivate"], ["edit", "materials"]],
    OM: [["edit", "materials", "copy", "deactivate"], ["edit", "materials"]],
    PM: [["edit", "materials", "copy", "deactivate"], ["edit", "materials"]],
    HR: [[], []],
    ASSET: [[], []],
    FINANCE: [[], []],
    KETUA: [[], []],
    ANGGOTA: [[], []],
  };
  it.each(Object.keys(PERAN) as Peran[])("%s", (peran) => {
    expect(workTypeActions(PERAN[peran], true)).toEqual(expected[peran][0]);
    expect(workTypeActions(PERAN[peran], false)).toEqual(expected[peran][1]);
  });
});

describe("Aset: peran × status × sudah diserahkan × jenis", () => {
  // Pengelola aset (manage:assets): serahkan hanya status siap; status hanya bila belum dipinjam.
  // Berkas kendaraan selalu ada. Peran lain (tanpa manage:assets) tidak melihat tombol alat.
  type Row = [kind: "VEHICLE" | "TOOL", status: string, assigned: boolean, expected: string[]];
  const pengelola: Row[] = [
    ["VEHICLE", "ready", false, ["lend", "files", "status"]],
    ["VEHICLE", "ready", true, ["lend", "files"]],
    ["VEHICLE", "maintenance", false, ["files", "status"]],
    ["VEHICLE", "maintenance", true, ["files"]],
    ["TOOL", "ready", false, ["lend", "status"]],
    ["TOOL", "ready", true, ["lend"]],
    ["TOOL", "maintenance", false, ["status"]],
    ["TOOL", "maintenance", true, []],
  ];
  const lainnya: Row[] = [
    ["VEHICLE", "ready", false, ["files"]],
    ["VEHICLE", "maintenance", true, ["files"]],
    ["TOOL", "ready", false, []],
    ["TOOL", "maintenance", true, []],
  ];

  for (const peran of Object.keys(PERAN) as Peran[]) {
    const manage = canManageAssets(PERAN[peran]);
    const rows = manage ? pengelola : lainnya;
    it.each(rows)(`${peran} (${manage ? "pengelola" : "bukan pengelola"}) %s %s assigned=%s`, (kind, status, assigned, want) => {
      expect(assetRowActions(manage, kind, status, assigned)).toEqual(want);
    });
  }

  it("hanya SUPER_ADMIN, ADMIN, HR, dan ASSET yang pengelola aset", () => {
    const pengelolaAset = (Object.keys(PERAN) as Peran[]).filter((p) => canManageAssets(PERAN[p]));
    expect(pengelolaAset).toEqual(["SUPER_ADMIN", "ADMIN", "HR", "ASSET"]);
  });
});

describe("Mess: peran", () => {
  const expected: Record<Peran, string[]> = {
    SUPER_ADMIN: ["manageStays", "managePlaces", "reviewRequests"],
    ADMIN: ["manageStays", "managePlaces", "reviewRequests"],
    OM: ["reviewRequests"],
    PM: ["reviewRequests"],
    HR: ["manageStays", "managePlaces", "reviewRequests"],
    ASSET: [],
    FINANCE: [],
    KETUA: [],
    ANGGOTA: [],
  };
  it.each(Object.keys(PERAN) as Peran[])("%s", (peran) => {
    expect(messActions(PERAN[peran])).toEqual(expected[peran]);
  });
});
