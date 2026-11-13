import { describe, expect, it } from "vitest";
import { tahapJatuhTempo } from "./dokumenKendaraan";

describe("tahapJatuhTempo", () => {
  it("memberi kalimat awam dan warna sesuai sisa hari", () => {
    expect(tahapJatuhTempo(12)).toEqual({ label: "Jatuh tempo 12 hari lagi", tone: "warning" });
    expect(tahapJatuhTempo(-3)).toEqual({ label: "Sudah lewat 3 hari", tone: "danger" });
    expect(tahapJatuhTempo(0).label).toBe("Jatuh tempo hari ini");
    expect(tahapJatuhTempo(7).tone).toBe("danger");
    expect(tahapJatuhTempo(60).tone).toBe("info");
  });
});
