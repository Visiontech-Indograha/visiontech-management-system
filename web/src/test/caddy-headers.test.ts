import { describe, expect, it } from "vitest";
import caddy from "../../Caddyfile?raw";

/** Regresi: Permissions-Policy `camera=()` memblokir kamera di seluruh situs (tak ada permintaan izin, absen/swafoto/wajah gagal). */
describe("Header keamanan Caddy", () => {
  const policy = /Permissions-Policy\s+"([^"]+)"/.exec(caddy)?.[1] ?? "";

  it("mengizinkan kamera dan lokasi untuk situs sendiri, mikrofon tetap diblokir", () => {
    expect(policy).toContain("camera=(self)");
    expect(policy).toContain("geolocation=(self)");
    expect(policy).toContain("microphone=()");
    expect(policy).not.toContain("camera=()");
  });

  it("CSP tidak memblokir pratinjau kamera dan pengunggahan gambar (blob/data)", () => {
    const csp = /Content-Security-Policy\s+"([^"]+)"/.exec(caddy)?.[1] ?? "";
    expect(csp).toMatch(/img-src[^;]*blob:/);
  });
});
