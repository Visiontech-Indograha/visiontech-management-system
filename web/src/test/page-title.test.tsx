import { waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { pageTitle } from "@/app/pageTitle";
import { mockApi, renderRoute } from "./utils";

describe("Judul tab peramban", () => {
  it("dinamis per halaman, termasuk rute berparameter dan tak dikenal", () => {
    expect(pageTitle("/")).toBe("Beranda · Visiontech VMS");
    expect(pageTitle("/attendance")).toBe("Absensi · Visiontech VMS");
    expect(pageTitle("/sites/")).toBe("Lokasi kerja · Visiontech VMS");
    expect(pageTitle("/directory/e1")).toBe("Detail karyawan · Visiontech VMS");
    expect(pageTitle("/login")).toBe("Masuk · Visiontech VMS");
    expect(pageTitle("/tidak-ada")).toBe("Halaman tidak ditemukan · Visiontech VMS");
  });

  it("document.title berubah mengikuti rute yang dibuka", async () => {
    mockApi(() => undefined);
    renderRoute("/login", { role: null });
    await waitFor(() => expect(document.title).toBe("Masuk · Visiontech VMS"));
  });
});
