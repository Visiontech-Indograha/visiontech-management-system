import { describe, expect, it } from "vitest";
import { checklistBlocker, inspectionSchema, rejectReasonSchema } from "./inspectionSchemas";

const ok = { vehicle_id: "v1", period_type: "DAILY", odometer_km: "", notes: "" };

describe("inspectionSchema", () => {
  it("menerima isian minimal", () => expect(inspectionSchema.safeParse(ok).success).toBe(true));
  it("menolak kendaraan kosong dan odometer di luar batas", () => {
    expect(inspectionSchema.safeParse({ ...ok, vehicle_id: "" }).success).toBe(false);
    expect(inspectionSchema.safeParse({ ...ok, odometer_km: "10000001" }).success).toBe(false);
    expect(inspectionSchema.safeParse({ ...ok, odometer_km: "-1" }).success).toBe(false);
  });
  it("menolak catatan lebih dari 1000 karakter", () => {
    expect(inspectionSchema.safeParse({ ...ok, notes: "a".repeat(1001) }).success).toBe(false);
  });
});

describe("rejectReasonSchema dan checklistBlocker", () => {
  it("alasan tolak wajib", () => {
    expect(rejectReasonSchema.safeParse("  ").success).toBe(false);
    expect(rejectReasonSchema.safeParse("Foto buram").success).toBe(true);
  });
  it("butir belum dijawab menghalangi kirim", () => {
    expect(checklistBlocker(["a", "b"], { a: "BAIK" }, 0)).toMatch(/dijawab/);
    expect(checklistBlocker(["a"], { a: "BAIK" }, 11)).toMatch(/maksimal 10/);
    expect(checklistBlocker(["a"], { a: "BAIK" }, 2)).toBeNull();
  });
});
