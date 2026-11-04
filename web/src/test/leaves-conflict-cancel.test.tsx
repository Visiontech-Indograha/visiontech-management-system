import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { mockApi, renderRoute } from "./utils";

/** F6: persetujuan cuti yang bertabrakan dengan jadwal tim wajib dikonfirmasi. F7: pembatalan cuti yang disetujui. */
const FUTURE_DATE = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
const leave = (over: Record<string, unknown> = {}) => ({
  leave_id: "l1", employee_id: "e1", employee_name: "Uji Ketua", employee_no: "N1", division_name: "Sipil",
  leave_type: "SICK", start_date: FUTURE_DATE, end_date: FUTURE_DATE, total_days: 1, reason: "Keperluan keluarga",
  status: "PENDING", attachment_path: null, reviewed_by_name: null, rejection_note: null, cancel_note: null,
  conflicts: [], create_at: "2026-10-27T10:00:00Z", ...over,
});

describe("Persetujuan cuti dengan konflik jadwal tim", () => {
  it("HR wajib mengonfirmasi konflik sebelum menyetujui, lalu persetujuan dikirim dengan acknowledge_conflicts", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/leaves" && c.method === "get") {
        return {
          data: [leave({
            conflicts: [{ plan_id: "p1", work_date: "2026-11-02", team_name: "Tim Alfa", status: "ONGOING" }],
          })],
        };
      }
      if (c.url === "/leaves/l1/review") return { data: leave({ status: "APPROVED_BY_HR" }) };
    });
    renderRoute("/leaves", { me: { ...mockMe("HR")!, role: "ADMIN_HR_GA" } });

    fireEvent.click(await screen.findByRole("button", { name: "Tinjau cuti Uji Ketua" }));
    expect(await screen.findByText(/Peringatan: pemohon terjadwal di tim/)).toBeInTheDocument();

    const approve = screen.getByRole("button", { name: "Setujui Permohonan" });
    expect(approve).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: "Konfirmasi konflik jadwal tim" }));
    expect(approve).toBeEnabled();
    fireEvent.click(approve);

    await waitFor(() => expect(calls.some((c) => c.url === "/leaves/l1/review")).toBe(true));
    const review = calls.find((c) => c.url === "/leaves/l1/review");
    expect(review?.data).toMatchObject({ decision: "APPROVED", acknowledge_conflicts: true });
  });

  it("tanpa konflik, tombol setujui langsung aktif dan tidak mengirim konfirmasi", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/leaves" && c.method === "get") return { data: [leave()] };
      if (c.url === "/leaves/l1/review") return { data: leave({ status: "APPROVED_BY_HR" }) };
    });
    renderRoute("/leaves", { me: { ...mockMe("HR")!, role: "ADMIN_HR_GA" } });

    fireEvent.click(await screen.findByRole("button", { name: "Tinjau cuti Uji Ketua" }));
    const approve = await screen.findByRole("button", { name: "Setujui Permohonan" });
    expect(approve).toBeEnabled();
    fireEvent.click(approve);

    await waitFor(() => expect(calls.some((c) => c.url === "/leaves/l1/review")).toBe(true));
    const review = calls.find((c) => c.url === "/leaves/l1/review");
    expect(review?.data).not.toHaveProperty("acknowledge_conflicts");
  });
});

describe("Pembatalan cuti yang sudah disetujui", () => {
  it("pemohon membatalkan cuti disetujui dengan alasan", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/leaves" && c.method === "get") {
        return { data: [leave({ status: "APPROVED_BY_HR", employee_id: "e-lead", employee_name: "Uji Ketua" })] };
      }
      if (c.url === "/leaves/l1/cancel") return { data: leave({ status: "CANCELLED", cancel_note: "Sudah sembuh" }) };
    });
    renderRoute("/leaves", { role: "field" });

    fireEvent.click(await screen.findByRole("button", { name: "Batalkan cuti Uji Ketua" }));
    fireEvent.change(await screen.findByLabelText("Alasan Pembatalan"), { target: { value: "Sudah sembuh" } });
    fireEvent.click(screen.getByRole("button", { name: "Batalkan Cuti" }));

    await waitFor(() => expect(calls.some((c) => c.url === "/leaves/l1/cancel")).toBe(true));
    expect(calls.find((c) => c.url === "/leaves/l1/cancel")?.data).toEqual({ reason: "Sudah sembuh" });
  });

  it("alasan pembatalan wajib diisi sebelum permintaan dikirim", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/leaves" && c.method === "get") {
        return { data: [leave({ status: "APPROVED_BY_HR", employee_id: "e-lead" })] };
      }
    });
    renderRoute("/leaves", { role: "field" });

    fireEvent.click(await screen.findByRole("button", { name: "Batalkan cuti Uji Ketua" }));
    fireEvent.click(await screen.findByRole("button", { name: "Batalkan Cuti" }));

    expect(await screen.findByText(/Alasan pembatalan wajib diisi/)).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/leaves/l1/cancel")).toBe(false);
  });

  it("karyawan lain tidak melihat tombol batalkan cuti", async () => {
    mockApi((c) => {
      if (c.url === "/leaves" && c.method === "get") return { data: [leave({ status: "APPROVED_BY_HR" })] };
    });
    renderRoute("/leaves", { role: "field" });

    expect(await screen.findByText("Keperluan keluarga")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Batalkan cuti Uji Ketua" })).not.toBeInTheDocument();
  });
});
