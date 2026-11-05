import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

describe("Rekap absensi", () => {
  it("menampilkan baris per karyawan dan mengirim bulan", async () => {
    const calls = mockApi((c) =>
      c.url === "/recaps/attendance"
        ? {
            data: {
              month: "2026-10",
              employees: [{ employee_id: "e1", full_name: "Budi", days_present: 20, auto_valid: 18, needs_review: 1, approved: 1, rejected: 0 }],
            },
          }
        : undefined,
    );
    renderRoute("/attendance-recap", { role: "FINANCE" });
    expect((await screen.findAllByText("Budi")).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Bulan"), { target: { value: "2026-09" } });
    await waitFor(() => expect(calls[calls.length - 1].params).toEqual({ month: "2026-09" }));
  });

  it("kosong", async () => {
    mockApi((c) => (c.url === "/recaps/attendance" ? { data: { month: "2026-10", employees: [] } } : undefined));
    renderRoute("/attendance-recap", { role: "field" });
    expect(await screen.findByText("Belum ada data kehadiran untuk bulan ini. Pilih bulan lain di kolom Bulan.")).toBeInTheDocument();
  });
});
