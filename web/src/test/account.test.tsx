import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

/** M1 / P1-7: Akun & keamanan — ganti password bisa ditemukan, daftar perangkat, keluarkan perangkat. */

const sessions = [
  { id: "s1", device_label: "Web Login", ip_address: "10.0.0.2", user_agent: "Mozilla/5.0 (Windows NT 10.0) Chrome/140.0",
    issued_at: "2026-09-27T01:00:00Z", last_used_at: "2026-09-27T03:00:00Z", current: true },
  { id: "s2", device_label: "Android", ip_address: "10.0.0.9", user_agent: "Dart/3.9 (dart:io) Android",
    issued_at: "2026-09-26T01:00:00Z", last_used_at: null, current: false },
];

describe("Akun & keamanan", () => {
  it("tautan di menu, perangkat ini ditandai, perangkat lain bisa dikeluarkan satu per satu", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/auth/sessions") return { data: sessions };
      if (c.url === "/auth/sessions/s2/revoke") return { data: { message: "ok" } };
    });
    renderRoute("/account", { role: "PM" });

    expect(screen.getByRole("link", { name: "Akun & keamanan" })).toHaveAttribute("href", "/account");
    expect(await screen.findByRole("link", { name: "Ganti password" })).toHaveAttribute("href", "/change-password");
    const list = await screen.findByRole("region", { name: "Perangkat yang masuk" });
    expect(await within(list).findByText("Perangkat ini")).toBeInTheDocument();
    expect(within(list).getByText(/Chrome · Windows/)).toBeInTheDocument();
    expect(within(list).getByText(/Aplikasi Visiontech · Android/)).toBeInTheDocument();

    fireEvent.click(within(list).getByRole("button", { name: "Keluarkan Aplikasi Visiontech · Android" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/auth/sessions/s2/revoke")).toBe(true));
    expect(within(list).queryByRole("button", { name: /Keluarkan Chrome/ })).toBeNull(); // perangkat ini tidak bisa
  });

  it("keluarkan semua perangkat lain", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/auth/sessions") return { data: sessions };
      if (c.url === "/auth/sessions/revoke-others") return { data: { revoked: 1, message: "ok" } };
    });
    renderRoute("/account", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: "Keluarkan perangkat lain" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/auth/sessions/revoke-others")).toBe(true));
  });

  it("hanya satu perangkat: tombol keluarkan perangkat lain tidak tampil", async () => {
    mockApi((c) => (c.url === "/auth/sessions" ? { data: [sessions[0]] } : undefined));
    renderRoute("/account", { role: "field" });
    await screen.findByText("Perangkat ini");
    expect(screen.queryByRole("button", { name: "Keluarkan perangkat lain" })).toBeNull();
  });
});
