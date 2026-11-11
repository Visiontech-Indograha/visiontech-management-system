import { describe, expect, it } from "vitest";
import { appEnv } from "@/lib/appEnv";

describe("appEnv", () => {
  it("produksi/uji = null, development dan beta dikenali", () => {
    expect(appEnv({})).toBeNull();
    expect(appEnv({ MODE: "test" })).toBeNull();
    expect(appEnv({ MODE: "production", VITE_APP_ENV: "" })).toBeNull();
    expect(appEnv({ MODE: "development" })).toBe("development");
    expect(appEnv({ VITE_APP_ENV: "beta" })).toBe("beta");
  });
});
