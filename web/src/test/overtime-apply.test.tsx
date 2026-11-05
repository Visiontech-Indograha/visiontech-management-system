import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { apiError, mockApi, renderRoute } from "./utils";

const row = {
  id: "o1", daily_plan_id: "p1", employee_id: "e-lead", employee_name: "Sari", work_date: "2026-10-05",
  hours: 2, reason: "Kejar target", status: "PENDING_PM", can_review: false, created_at: "2026-10-05T10:00:00Z",
};
const plan = { daily_plan_id: "p1", team_name: "Tim A", work_date: "2026-10-05", status: "ONGOING" };

describe("Lembur saya", () => {
  it("menampilkan daftar dengan status", async () => {
    mockApi((c) => (c.url === "/overtime" ? { data: [row] } : undefined));
    renderRoute("/overtime", { role: "field" });
    expect(await screen.findByText("Alasan: Kejar target")).toBeInTheDocument();
    expect(screen.getByText("Menunggu PM")).toBeInTheDocument();
  });

  it("peninjau: Lembur saya hanya milik sendiri, antrean terpisah", async () => {
    const lain = { ...row, id: "o2", employee_id: "e9", employee_name: "Orang Lain", reason: "Punya orang lain", can_review: true };
    const saya = { ...row, id: "o3", employee_id: "e1", reason: "Punya saya" };
    mockApi((c) => {
      if (c.url !== "/overtime") return undefined;
      const p = c.params as { status?: string } | undefined;
      return { data: p?.status === "PENDING_PM" ? [lain] : [lain, saya] };
    });
    renderRoute("/overtime", { me: { ...mockMe("OPS"), employee_id: "e1" } as never });
    expect(await screen.findByText("Alasan: Punya saya")).toBeInTheDocument();
    expect(screen.getByText("Lembur saya")).toBeInTheDocument();
    expect(screen.getAllByText("Alasan: Punya orang lain")).toHaveLength(1);
  });

  it("kosong", async () => {
    mockApi((c) => (c.url === "/overtime" ? { data: [] } : undefined));
    renderRoute("/overtime", { role: "field" });
    expect(await screen.findByText("Belum ada pengajuan lembur.")).toBeInTheDocument();
  });

  it("galat memuat", async () => {
    mockApi((c) => (c.url === "/overtime" ? { status: 500, data: {} } : undefined));
    renderRoute("/overtime", { role: "field" });
    expect(await screen.findByText("Daftar lembur tidak dapat dimuat.")).toBeInTheDocument();
  });

  it("mengajukan lembur dengan kunci anti-ganda", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily") return { data: [plan] };
      if (c.url === "/overtime" && c.method === "post") return { status: 201, data: row };
      if (c.url === "/overtime") return { data: [] };
      return undefined;
    });
    renderRoute("/overtime", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: /Ajukan lembur/ }));
    await screen.findByLabelText("Jadwal kerja");
    fireEvent.change(screen.getByLabelText("Jadwal kerja"), { target: { value: "p1" } });
    fireEvent.change(screen.getByLabelText("Lama lembur (jam)"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Alasan"), { target: { value: "Kejar target" } });
    fireEvent.click(screen.getByRole("button", { name: "Kirim pengajuan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post")).toBe(true));
    const post = calls.find((c) => c.method === "post")!;
    expect(post.data).toMatchObject({ daily_plan_id: "p1", hours: 2, reason: "Kejar target" });
    expect(JSON.stringify(post.headers)).toContain("Idempotency-Key");
  });

  it("menolak jam di atas 12", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/daily") return { data: [plan] };
      if (c.url === "/overtime") return { data: [] };
      return undefined;
    });
    renderRoute("/overtime", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: /Ajukan lembur/ }));
    await screen.findByLabelText("Jadwal kerja");
    fireEvent.change(screen.getByLabelText("Jadwal kerja"), { target: { value: "p1" } });
    fireEvent.change(screen.getByLabelText("Lama lembur (jam)"), { target: { value: "13" } });
    fireEvent.change(screen.getByLabelText("Alasan"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Kirim pengajuan" }));
    expect(await screen.findByText(/paling banyak 12 jam/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post")).toBe(false);
  });

  it("galat 422 tampil di kolom", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/daily") return { data: [plan] };
      if (c.url === "/overtime" && c.method === "post")
        return apiError(422, "VALIDATION_ERROR", "Data tidak valid", { fields: { reason: "Alasan terlalu panjang." } });
      if (c.url === "/overtime") return { data: [] };
      return undefined;
    });
    renderRoute("/overtime", { role: "field" });
    fireEvent.click(await screen.findByRole("button", { name: /Ajukan lembur/ }));
    await screen.findByLabelText("Jadwal kerja");
    fireEvent.change(screen.getByLabelText("Jadwal kerja"), { target: { value: "p1" } });
    fireEvent.change(screen.getByLabelText("Lama lembur (jam)"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Alasan"), { target: { value: "abc" } });
    fireEvent.click(screen.getByRole("button", { name: "Kirim pengajuan" }));
    expect(await screen.findByText("Periksa kolom yang ditandai.")).toBeInTheDocument();
  });
});
