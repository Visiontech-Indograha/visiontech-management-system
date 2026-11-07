import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

describe("petunjuk pencarian awalan", () => {
  it("direktori karyawan menyebut awal nama, nomor, atau email", async () => {
    mockApi((c) => (c.url === "/employees" ? { data: { items: [], total: 0 } } : undefined));
    renderRoute("/directory", { role: "ADMIN" });
    expect(await screen.findByPlaceholderText("Cari awal nama, nomor, atau email...")).toBeInTheDocument();
  });

  it("daftar klien menyebut awal nama atau kode", async () => {
    mockApi((c) => (c.url === "/clients" ? { data: [] } : undefined));
    renderRoute("/clients", { role: "ADMIN" });
    expect(await screen.findByPlaceholderText("Cari awal nama atau kode klien...")).toBeInTheDocument();
  });

  it("placeholder email login tidak berubah", async () => {
    mockApi(() => undefined);
    renderRoute("/login", { role: null });
    expect(await screen.findByPlaceholderText("nama@visiontech.id")).toBeInTheDocument();
  });
});
