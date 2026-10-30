import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

const row = (over: Record<string, unknown>) => ({
  id: "o1", daily_plan_id: "p1", employee_id: "e1", employee_name: "Budi", employee_photo_file_id: null,
  work_date: "2026-10-28", hours: 2, reason: "Kabel tambahan", status: "PENDING_PM", reviewed_by: null,
  reviewed_at: null, review_note: null, created_at: "2026-10-28T10:00:00Z", can_review: true, ...over,
});

const recap = { data: [] };

describe("Tinjau lembur", () => {
  it("peninjau menyetujui lembur dan daftar tersegarkan", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/overtime" && c.method === "get") return { data: [row({})] };
      if (c.url === "/overtime/o1/review") return { data: row({ status: "APPROVED", can_review: false }) };
      if (c.url === "/recaps/overtime") return recap;
    });
    renderRoute("/overtime-recap", { role: "PM" });
    await userEvent.click(await screen.findByRole("button", { name: "Setujui lembur Budi" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/overtime/o1/review")).toBe(true));
    const post = calls.find((c) => c.url === "/overtime/o1/review");
    expect(post?.data).toEqual({ decision: "APPROVED", note: undefined });
  });

  it("tolak wajib beralasan, lalu dikirim sebagai REJECTED", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/overtime" && c.method === "get") return { data: [row({})] };
      if (c.url === "/overtime/o1/review") return { data: row({ status: "REJECTED", can_review: false }) };
      if (c.url === "/recaps/overtime") return recap;
    });
    renderRoute("/overtime-recap", { role: "OPS" });
    await userEvent.click(await screen.findByRole("button", { name: "Tolak lembur Budi" }));
    await userEvent.click(await screen.findByRole("button", { name: "Tolak lembur" }));
    expect(await screen.findByText("Alasan penolakan wajib diisi.")).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/overtime/o1/review")).toBe(false);
    await userEvent.type(screen.getByLabelText(/Alasan penolakan lembur Budi/), "Tidak ada perintah");
    await userEvent.click(screen.getByRole("button", { name: "Tolak lembur" }));
    await waitFor(() =>
      expect(calls.find((c) => c.url === "/overtime/o1/review")?.data).toEqual({
        decision: "REJECTED",
        note: "Tidak ada perintah",
      }),
    );
  });

  it("lembur yang bukan wewenang pengguna tampil tanpa tombol", async () => {
    mockApi((c) => {
      if (c.url === "/overtime" && c.method === "get") return { data: [row({ can_review: false })] };
      if (c.url === "/recaps/overtime") return recap;
    });
    renderRoute("/overtime-recap", { role: "PM" });
    expect(await screen.findByText("Budi")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Setujui lembur Budi" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tolak lembur Budi" })).not.toBeInTheDocument();
  });

  it("lembur yang sudah diputuskan tidak punya tombol", async () => {
    mockApi((c) => {
      if (c.url === "/overtime" && c.method === "get") return { data: [row({ status: "APPROVED" })] };
      if (c.url === "/recaps/overtime") return recap;
    });
    renderRoute("/overtime-recap", { role: "ADMIN" });
    expect(await screen.findByText("Budi")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Setujui lembur Budi" })).not.toBeInTheDocument();
  });
});
