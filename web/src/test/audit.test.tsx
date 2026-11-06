import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const event = {
  id: "a1",
  occurred_at: "2026-09-20T02:00:00Z",
  actor_label: "hr@example.com",
  action: "UPDATE",
  entity_type: "employee_document",
  entity_id: "d1d1d1d1-0000",
  detail: null,
  changes: { status: { dari: "PENDING", menjadi: "VALID" } },
};

describe("Audit log", () => {
  it("menampilkan kejadian dengan label entitas dan aksi", async () => {
    mockApi((c) => (c.url === "/audit-events" ? { data: { items: [event], total: 1, page: 1, size: 25 } } : undefined));
    renderRoute("/audit-logs", { role: "ADMIN" });
    expect(await screen.findByText("Ubah")).toBeInTheDocument();
    expect(screen.getByText(/Berkas karyawan/, { selector: "td" })).toBeInTheDocument();
  });

  it("filter entitas dikirim sebagai entity_type", async () => {
    const calls = mockApi((c) =>
      c.url === "/audit-events" ? { data: { items: [], total: 0, page: 1, size: 25 } } : undefined,
    );
    renderRoute("/audit-logs", { role: "ADMIN" });
    await screen.findByText("Belum ada catatan.");
    fireEvent.change(screen.getByLabelText("Filter entitas"), { target: { value: "work_plan" } });
    await waitFor(() => expect(calls[calls.length - 1]?.params).toMatchObject({ entity_type: "work_plan", cursor: "" }));
  });

  it("galat menampilkan tombol Coba lagi", async () => {
    mockApi(() => apiError(500, "INTERNAL_ERROR", "Terjadi gangguan pada sistem. Coba lagi beberapa saat; bila berulang, hubungi admin."));
    renderRoute("/audit-logs", { role: "ADMIN" });
    expect(await screen.findByRole("button", { name: "Coba lagi" })).toBeInTheDocument();
  });
});

describe("label awam audit", () => {
  it("label sidik jari dan nama peran pelaku", async () => {
    const { ACTION_LABEL, actorLabelAwam } = await import("@/lib/auditLabels");
    expect(ACTION_LABEL.DEVICE_CRED_ISSUED).toBe("Kunci perangkat dibuat untuk login sidik jari");
    expect(ACTION_LABEL.DEVICE_CRED_USED).toBe("Masuk dengan sidik jari");
    expect(ACTION_LABEL.DEVICE_CRED_REVOKED).toBe("Kunci perangkat sidik jari dicabut");
    expect(ACTION_LABEL.DEVICE_CRED_REUSE).toBe("Kunci perangkat dipakai ulang, dicabut demi keamanan");
    expect(actorLabelAwam("a@x.id (SUPER_ADMIN)")).toBe("a@x.id (Super Admin)");
    expect(actorLabelAwam("a@x.id (TEAM_LEADER)")).toBe("a@x.id (Ketua tim)");
  });
});
