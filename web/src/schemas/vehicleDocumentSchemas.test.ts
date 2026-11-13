import { describe, expect, it } from "vitest";
import { vehicleDocumentSchema } from "./vehicleDocumentSchemas";

const ok = { doc_type_code: "STNK", doc_no: "", issued_on: "", expired_on: "2026-12-01", catatan: "" };

describe("vehicleDocumentSchema", () => {
  it("menolak jenis/jatuh tempo kosong, catatan terlalu panjang, dan tanggal terbalik", () => {
    expect(vehicleDocumentSchema.safeParse(ok).success).toBe(true);
    expect(vehicleDocumentSchema.safeParse({ ...ok, doc_type_code: "" }).success).toBe(false);
    expect(vehicleDocumentSchema.safeParse({ ...ok, expired_on: "" }).success).toBe(false);
    expect(vehicleDocumentSchema.safeParse({ ...ok, catatan: "x".repeat(501) }).success).toBe(false);
    expect(vehicleDocumentSchema.safeParse({ ...ok, issued_on: "2027-01-01" }).success).toBe(false);
  });
});
