import { describe, expect, it } from "vitest";
import { deviceSchema, isIpAddress, mappingSchema } from "./hikvisionSchemas";

const ok = { office_id: "o", name: "Pintu depan", ip_address: "192.168.1.20", http_port: "80", serial_no: "DS-K1T.1", model: "", catatan: "", aktif: "ya" as const };

describe("skema mesin absensi", () => {
  it("menerima isian benar", () => expect(deviceSchema.safeParse(ok).success).toBe(true));
  it("menolak IP, port, dan nomor seri di luar batas API", () => {
    expect(isIpAddress("300.1.1.1")).toBe(false);
    expect(deviceSchema.safeParse({ ...ok, ip_address: "abc" }).success).toBe(false);
    expect(deviceSchema.safeParse({ ...ok, http_port: "70000" }).success).toBe(false);
    expect(deviceSchema.safeParse({ ...ok, serial_no: "a b" }).success).toBe(false);
  });
  it("pemetaan: nomor di mesin dibatasi pola API", () => {
    expect(mappingSchema.safeParse({ employee_no_string: "12 3", employee_id: "x" }).success).toBe(false);
    expect(mappingSchema.safeParse({ employee_no_string: "123", employee_id: "x" }).success).toBe(true);
  });
});
