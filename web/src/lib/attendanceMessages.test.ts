import { describe, expect, it } from "vitest";
import { checkInMessage } from "./attendanceMessages";

describe("checkInMessage", () => {
  it("wajah belum terdaftar: pesan benar, bukan soal jarak", () => {
    const m = checkInMessage({ status: "NEEDS_REVIEW", face_status: "NOT_ENROLLED" }, "0 m");
    expect(m).toContain("wajah Anda belum terdaftar");
    expect(m).toContain("Hubungi HR");
    expect(m).not.toContain("0 m");
  });
  it("perlu ditinjau karena hal lain", () => {
    expect(checkInMessage({ status: "NEEDS_REVIEW" }, "2,5 km")).toContain("menunggu ditinjau");
  });
  it("normal", () => {
    expect(checkInMessage({ status: "VALID" }, "0 m")).toBe("Absen masuk tercatat.");
  });
});
