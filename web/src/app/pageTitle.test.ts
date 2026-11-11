import { describe, expect, it } from "vitest";
import { pageTitle } from "@/app/pageTitle";

describe("pageTitle awalan lingkungan", () => {
  it("diberi awalan DEV/BETA, produksi tanpa awalan", () => {
    expect(pageTitle("/login", "development")).toBe("[DEV] Masuk · Visiontech VMS");
    expect(pageTitle("/login", "beta")).toBe("[BETA] Masuk · Visiontech VMS");
    expect(pageTitle("/login", null)).toBe("Masuk · Visiontech VMS");
  });
});
