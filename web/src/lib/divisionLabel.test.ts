import { describe, expect, it } from "vitest";
import { divisionOptionLabel } from "./divisionLabel";

describe("divisionOptionLabel", () => {
  const semua = [
    { name: "Instalasi", code: "DIV-INS" },
    { name: "QA", code: "DIV-QA-1" },
    { name: "QA", code: "DIV-QA-2" },
  ];
  it("nama saja bila unik", () => expect(divisionOptionLabel(semua[0], semua)).toBe("Instalasi"));
  it("tambah kode hanya bila nama kembar", () => expect(divisionOptionLabel(semua[1], semua)).toBe("QA (DIV-QA-1)"));
});
