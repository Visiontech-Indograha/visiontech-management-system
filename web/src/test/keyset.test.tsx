import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, renderRoute } from "./utils";

const audit = (id: string, actor: string) => ({
  id, occurred_at: "2026-09-20T02:00:00Z", actor_label: actor, action: "UPDATE",
  entity_type: "employee_document", entity_id: "d1", detail: null, changes: {},
});
const att = (id: string, site: string) => ({
  id, employee_id: "e1", work_date: "2026-10-02", site_id: "s1", site_label: site,
  check_in_at: "2026-10-02T00:30:00Z", check_out_at: null, distance_m: 10, is_late: false, is_early_leave: false,
  status: "NEEDS_REVIEW", explanation: null, reviewed_at: null, employee_name: "Budi", selfie_file_id: null, can_review: false,
});
const ot = (id: string, reason: string) => ({
  id, daily_plan_id: "p1", employee_id: "e1", employee_name: "Budi", employee_photo_file_id: null,
  work_date: "2026-10-28", hours: 2, reason, status: "PENDING_PM", reviewed_by: null,
  reviewed_at: null, review_note: null, created_at: "2026-10-28T10:00:00Z", can_review: true,
});

interface Case {
  name: string;
  url: string;
  route: string;
  role: string;
  maxSize: number;
  page: (n: 1 | 2) => unknown;
  first: string;
  second: string;
}

const attPage = (n: 1 | 2) => ({
  items: [n === 1 ? att("a1", "Gudang Satu") : att("a2", "Gudang Dua")], total: 0, page: 1, size: 50,
});
const cases: Case[] = [
  {
    name: "audit log", url: "/audit-events", route: "/audit-logs", role: "ADMIN", maxSize: 100,
    page: (n) => ({ items: [n === 1 ? audit("x1", "satu@example.com") : audit("x2", "dua@example.com")], total: 0, page: 1, size: 25 }),
    first: "satu@example.com", second: "dua@example.com",
  },
  {
    name: "absensi", url: "/attendance", route: "/attendance", role: "FINANCE", maxSize: 200,
    page: attPage, first: "Gudang Satu", second: "Gudang Dua",
  },
  {
    name: "lembur", url: "/overtime", route: "/overtime-recap", role: "PM", maxSize: 100,
    page: (n) => [n === 1 ? ot("o1", "Alasan satu") : ot("o2", "Alasan dua")],
    first: "Alasan satu", second: "Alasan dua",
  },
];

const recap = { data: [] };

describe.each(cases)("Pagination keyset: $name", (c) => {
  const serve = (handler: (cursor: string) => { status?: number; data?: unknown; headers?: Record<string, string> }) =>
    mockApi((cfg) => {
      if (cfg.url === c.url && (cfg.method ?? "get") === "get") {
        return handler(String((cfg.params as { cursor?: string }).cursor));
      }
      if (cfg.url === "/recaps/overtime") return recap;
      if (cfg.url === "/employees") return { data: { items: [], total: 0, page: 1, size: 100 } };
    });

  it("halaman pertama mengirim cursor kosong, size sesuai batas, tanpa total", async () => {
    const calls = serve(() => ({ data: c.page(1) }));
    renderRoute(c.route, { role: c.role });
    expect(await screen.findByText(c.first, { exact: false })).toBeInTheDocument();
    const p = calls.find((x) => x.url === c.url)!.params as { cursor: string; size: number };
    expect(p.cursor).toBe("");
    expect(p.size).toBeLessThanOrEqual(c.maxSize);
    expect(screen.queryByRole("button", { name: "Muat lebih banyak" })).not.toBeInTheDocument();
    expect(screen.queryByText(/halaman \d+ dari/)).not.toBeInTheDocument();
    expect(screen.queryByText(/\d+ catatan/)).not.toBeInTheDocument();
  });

  it("Muat lebih banyak memakai X-Next-Cursor dan menambah baris", async () => {
    const calls = serve((cur) =>
      cur === "" ? { data: c.page(1), headers: { "x-next-cursor": "KURSOR-2" } } : { data: c.page(2) },
    );
    renderRoute(c.route, { role: c.role });
    await userEvent.click(await screen.findByRole("button", { name: "Muat lebih banyak" }));
    expect(await screen.findByText(c.second, { exact: false })).toBeInTheDocument();
    expect(screen.getByText(c.first, { exact: false })).toBeInTheDocument();
    expect(calls.filter((x) => x.url === c.url).map((x) => (x.params as { cursor: string }).cursor)).toContain("KURSOR-2");
    await waitFor(() => expect(screen.queryByRole("button", { name: "Muat lebih banyak" })).not.toBeInTheDocument());
  });

  it("kursor tidak valid (422) menampilkan pesan dan mulai ulang dari awal", async () => {
    let bad = true;
    const calls = serve((cur) => {
      if (cur === "") return { data: c.page(1), headers: { "x-next-cursor": "RUSAK" } };
      bad = false;
      return apiError(422, "VALIDATION_ERROR", "Kursor halaman tidak valid. Muat ulang daftar dari awal.");
    });
    renderRoute(c.route, { role: c.role });
    await userEvent.click(await screen.findByRole("button", { name: "Muat lebih banyak" }));
    expect(await screen.findByText("Daftar sudah berubah, jadi dimuat ulang dari awal.")).toBeInTheDocument();
    expect(bad).toBe(false);
    await waitFor(() => {
      const cursors = calls.filter((x) => x.url === c.url).map((x) => (x.params as { cursor: string }).cursor);
      expect(cursors.filter((v) => v === "").length).toBeGreaterThanOrEqual(2);
    });
    expect(await screen.findByText(c.first, { exact: false })).toBeInTheDocument();
  });
});
