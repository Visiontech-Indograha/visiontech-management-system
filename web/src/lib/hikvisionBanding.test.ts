import { describe, expect, it } from "vitest";
import type { components } from "@/lib/apiTypes";
import { cocokAwalan, selisihLabel, statusBanding } from "./hikvisionBanding";

type BandingBaris = components["schemas"]["BandingBaris"];
const base = {
  employee_id: "e", employee_name: "Budi", tgl: "2026-11-10", pertama: "", terakhir: "", jumlah: 2,
  clock_in_at: "x", clock_out_at: "y", selisih_masuk_menit: 1, selisih_pulang_menit: -2,
} as BandingBaris;

describe("hikvisionBanding", () => {
  it("cocok bila selisih dalam toleransi", () => expect(statusBanding(base)).toBe("cocok"));
  it("waktu berbeda bila selisih melewati toleransi", () =>
    expect(statusBanding({ ...base, selisih_masuk_menit: 12 })).toBe("selisih"));
  it("hanya di mesin bila tanpa absen aplikasi", () =>
    expect(statusBanding({ ...base, clock_in_at: null, clock_out_at: null, selisih_masuk_menit: null, selisih_pulang_menit: null })).toBe("hanya_mesin"));
  it("selisih memakai kalimat awam", () => {
    expect(selisihLabel(null)).toBe("-");
    expect(selisihLabel(0)).toBe("Sama");
    expect(selisihLabel(7)).toBe("7 menit lebih lambat di mesin");
    expect(selisihLabel(-3)).toBe("3 menit lebih awal di mesin");
  });
  it("cari hanya awalan", () => {
    expect(cocokAwalan("Budi Santoso", "bu")).toBe(true);
    expect(cocokAwalan("Budi Santoso", "santoso")).toBe(false);
  });
});
