import { describe, expect, it } from "vitest";
import { AUDIT_ENTITIES, AUDIT_FILTER_ENTITIES } from "./auditLabels";
import { actionLabel, describeChanges, entityLabel, resolveAuditSearch } from "./auditChanges";

describe("label audit baru", () => {
  it("memetakan aksi dan entitas, dengan fallback kode asli", () => {
    expect(actionLabel("CLIENT_CREATE")).toBe("Menambah klien");
    expect(actionLabel("HARD_DELETE")).toBe("Dihapus permanen");
    expect(actionLabel("ZZZ_BARU")).toBe("ZZZ_BARU");
    expect(entityLabel("employee")).toBe("Karyawan");
    expect(entityLabel("xyz")).toBe("xyz");
    expect(AUDIT_ENTITIES.office).toBe("Lokasi kerja");
    expect(Object.values(AUDIT_FILTER_ENTITIES)).toEqual(
      expect.arrayContaining(["Lokasi kerja", "Klien", "Alat", "Kendaraan", "Karyawan", "Akun pengguna"]),
    );
  });

  it("menjabarkan perubahan dan menyembunyikan nilai rahasia", () => {
    const lines = describeChanges({ changes: { name: { old: "A", new: "B" }, foo: { new: 1 } }, masked_changed: ["address"] });
    expect(lines).toEqual([
      { label: "Nama", text: "A -> B" },
      { label: "foo", text: "1" },
      { label: "Alamat", text: "diubah (nilai disembunyikan)" },
    ]);
    expect(describeChanges(null)).toEqual([]);
  });

  it("pencarian mengenali label aksi", () => {
    expect(resolveAuditSearch("Menambah klien")).toBe("CLIENT_CREATE");
    expect(resolveAuditSearch("budi")).toBe("budi");
  });
});
