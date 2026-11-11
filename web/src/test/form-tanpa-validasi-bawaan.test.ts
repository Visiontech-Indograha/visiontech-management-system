import { describe, expect, it } from "vitest";

const sumber = import.meta.glob(
  [
    "../components/organisms/clients/ClientSitesModal.tsx",
    "../components/organisms/work-orders/WorkOrder{Assign,Bast,Create}Modal.tsx",
  ],
  { query: "?raw", import: "default", eager: true },
) as Record<string, string>;

describe("Formulir tanpa pesan bawaan browser (Inggris)", () => {
  it("keempat formulir memakai noValidate", () => {
    const berkas = Object.entries(sumber);
    expect(berkas.length).toBe(4);
    for (const [, isi] of berkas) expect(isi).toMatch(/<FormBlock[^>]*noValidate/);
  });
});
