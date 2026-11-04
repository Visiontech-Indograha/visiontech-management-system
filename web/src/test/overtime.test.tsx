import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

describe("Lembur", () => {
  it("rekap lembur bulanan", async () => {
    const calls = mockApi((c) =>
      c.url === "/recaps/overtime"
        ? { data: [{ employee_id: "e1", employee_name: "Budi", period_month: "2026-10-01", approved_entries: 2, pending_entries: 1, approved_hours: 5.5 }] }
        : undefined,
    );
    renderRoute("/overtime-recap", { role: "FINANCE" });
    expect(await screen.findByText("Budi")).toBeInTheDocument();
    expect(screen.getByText("5.5")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Bulan"), { target: { value: "2026-09" } });
    await waitFor(() => expect(calls[calls.length - 1].params).toEqual({ month: "2026-09" }));
  });

  it("rekap lembur ditolak untuk karyawan biasa", () => {
    mockApi(() => undefined);
    const { router } = renderRoute("/overtime-recap", { role: "field" });
    expect(router.state.location.pathname).toBe("/403");
  });
});
