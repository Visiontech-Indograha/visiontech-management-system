import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { mockApi, renderRoute } from "./utils";

describe("Tombol Ajukan lembur per peran", () => {
  it.each([
    ["EMPLOYEE", true],
    ["TEAM_LEADER", true],
    ["OPS", false],
    ["FINANCE", false],
  ])("peran %s -> tombol tampil: %s", async (role, tampil) => {
    mockApi((c) => (c.url === "/overtime" ? { data: [] } : undefined));
    renderRoute("/overtime", { me: { ...mockMe("OPS"), role, employee_id: "e1" } as never });
    await screen.findByText("Belum ada pengajuan lembur.");
    expect(screen.queryByRole("button", { name: /Ajukan lembur/ }) !== null).toBe(tampil);
  });
});
