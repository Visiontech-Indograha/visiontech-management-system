import { describe, expect, it } from "vitest";
import { accuracyText, reviewReasonInfo, reviewReasonTexts } from "./reviewReasons";

describe("reviewReasons", () => {
  it("wajah belum terdaftar punya aksi daftar", () => {
    expect(reviewReasonInfo("FACE_NOT_ENROLLED").action).toBe("ENROLL");
    expect(reviewReasonInfo("LOKASI_KASAR").text).toMatch(/laptop tanpa GPS/);
  });
  it("kode tak dikenal tidak membocorkan kode", () => {
    expect(reviewReasonTexts(["XYZ", "ABC"])).toEqual(["Absen Anda perlu ditinjau HR."]);
  });
  it("akurasi", () => {
    expect(accuracyText(412.4)).toBe("Akurasi lokasi ±412 m");
    expect(accuracyText(null)).toBeNull();
  });
});
