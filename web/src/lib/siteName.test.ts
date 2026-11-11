import { describe, expect, it } from "vitest";
import { duplicateSiteName } from "./siteName";

const sites = [{ id: "1", name: "Kantor Pusat" }, { id: "2", name: "Gudang" }];

describe("duplicateSiteName", () => {
  it("mendeteksi nama kembar tanpa beda huruf", () => expect(duplicateSiteName(" kantor pusat ", sites)).toBe(true));
  it("mengabaikan lokasi yang sedang diubah", () => expect(duplicateSiteName("Gudang", sites, "2")).toBe(false));
  it("nama kosong atau baru bukan kembar", () => {
    expect(duplicateSiteName("", sites)).toBe(false);
    expect(duplicateSiteName("Baru", sites)).toBe(false);
  });
});
