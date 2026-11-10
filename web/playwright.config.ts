import { defineConfig } from "@playwright/test";
import { BASE_URL } from "./e2e/env";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.spec\.ts/,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: BASE_URL, locale: "id-ID", trace: "retain-on-failure" },
});
