import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

// docs/32: tautan pemasangan pertama aplikasi HP di halaman login — hanya bila sudah ada rilis.
describe("tautan unduh aplikasi Android di halaman login", () => {
  it("tampil dengan versi, build, dan ukuran bila ada rilis", async () => {
    const calls = mockApi((request) => {
      if (request.url === "/app/android/update") {
        return { data: { latest_build: 4, latest_version: "1.2.0", download: { size: 25 * 1024 * 1024 } } };
      }
    });
    renderRoute("/login", { me: null });
    const link = await screen.findByTestId("unduh-aplikasi-android");
    expect(link).toHaveTextContent("versi 1.2.0 (build 4) · 25 MB");
    expect(link).toHaveAttribute("href", "/api/v1/app/android/latest.apk");
    expect(calls.some((c) => c.url === "/app/android/update" && (c.params as { build?: number } | undefined)?.build === 0)).toBe(true);
  });

  it("tidak tampil bila belum ada rilis", async () => {
    const calls = mockApi((request) => {
      if (request.url === "/app/android/update") return { data: { latest_build: null, download: null } };
    });
    renderRoute("/login", { me: null });
    await waitFor(() => expect(calls.some((c) => c.url === "/app/android/update")).toBe(true));
    expect(screen.queryByTestId("unduh-aplikasi-android")).not.toBeInTheDocument();
  });
});
