import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { CorrectionsPanel } from "@/components/organisms/work-plans/CorrectionsPanel";
import { apiError, mockApi } from "./utils";

const correction = (status: string) => ({
  correction_id: "c1", daily_plan_id: "p1", site_name: "Gardu Induk", team_name: "Tim Alpha",
  work_date: "2026-10-28", status, requested_by_name: "Agus", reason: "Foto kurang", review_note: null,
});

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <CorrectionsPanel canDecide />
    </QueryClientProvider>,
  );
}

describe("CorrectionsPanel", () => {
  it("klik pertama 'Setujui revisi' langsung memperbarui daftar (tanpa klik kedua)", async () => {
    let status = "REQUESTED";
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/corrections" && c.method === "get") return { data: [correction(status)] };
      if (c.url === "/work-plans/corrections/c1/decision") {
        status = "REVISING";
        return { data: correction(status) };
      }
    });
    renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: "Setujui revisi" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url.endsWith("/decision"))).toBe(true));
    // Daftar harus di-refetch: status baru tampil, tombol lama hilang.
    expect(await screen.findByText(/Sedang direvisi ketua/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Setujui revisi" })).toBeNull();
  });

  it("F9: terima ditolak bila foto wajib belum lengkap; 'Terima tetap dengan catatan' mengirim force", async () => {
    let status = "IN_REVIEW";
    const calls = mockApi((c) => {
      if (c.url === "/work-plans/corrections" && c.method === "get") return { data: [correction(status)] };
      if (c.url === "/work-plans/corrections/c1/decision") {
        const body = JSON.parse(String(c.data)) as { decision: string; force?: boolean };
        if (body.decision === "ACCEPT" && !body.force) {
          return apiError(409, "PHOTOS_INCOMPLETE", "Foto wajib belum lengkap (AP B: Foto sesudah). Minta ketua melengkapi.");
        }
        status = "ACCEPTED";
        return { data: correction(status) };
      }
    });
    renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: "Terima laporan" }));
    const warning = await screen.findByRole("alert");
    expect(warning.textContent).toContain("Foto wajib belum lengkap");
    fireEvent.click(screen.getByRole("button", { name: "Terima tetap dengan catatan" }));
    fireEvent.change(await screen.findByLabelText("Catatan untuk ketua tim"), { target: { value: "Foto menyusul" } });
    fireEvent.submit(document.querySelector("form#correction-note-form") as HTMLFormElement);
    await waitFor(() => {
      const posts = calls.filter((c) => c.method === "post" && c.url.endsWith("/decision"));
      expect(posts[posts.length - 1]?.data).toEqual({ decision: "ACCEPT", note: "Foto menyusul", force: true });
    });
  });
});
