import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkCompletionExportPanel } from "@/components/organisms/work-completions/WorkCompletionExportPanel";
import { mockApi, renderRoute } from "./utils";

/** Milestone 8: ekspor dokumen resmi order + halaman verifikasi QR publik. */

const HASH = "ab".repeat(32);

function renderPanel(signed: boolean) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <WorkCompletionExportPanel completionId="c-1" signed={signed} />
    </QueryClientProvider>,
  );
}

describe("Ekspor dokumen order", () => {
  beforeEach(() => {
    window.URL.createObjectURL = vi.fn(() => "blob:x");
    window.URL.revokeObjectURL = vi.fn();
  });

  it("PDF resmi terkunci sebelum PM menandatangani; dokumen lain tersedia", async () => {
    mockApi((c) => (c.url === "/exports/work-completions/c-1" ? { data: [] } : undefined));
    renderPanel(false);
    expect(screen.getByRole("button", { name: /Serah terima resmi \(\.pdf\)/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Laporan survei \(\.docx\)/ })).toBeEnabled();
  });

  it("membuat Survey Report lewat POST lalu menampilkan riwayat yang bisa diunduh ulang", async () => {
    let created = false;
    const calls = mockApi((c) => {
      if (c.method === "post" && c.url === "/exports/work-completions/c-1") {
        created = true;
        return { data: new Blob(["docx"]) };
      }
      if (c.url === "/exports/work-completions/c-1") {
        return {
          data: created
            ? [{ export_id: "x-1", source_type: "WORK_COMPLETION", completion_id: "c-1", template_type: "SURVEY_REPORT",
                 export_format: "WORD_DOCX", generated_by_id: "e-1", generated_by_name: "Dian",
                 create_at: "2026-10-21T03:00:00Z", file_name: "SURVEY_REPORT.docx" }]
            : [],
        };
      }
    });
    renderPanel(true);
    fireEvent.click(screen.getByRole("button", { name: /Laporan survei \(\.docx\)/ }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "post")?.data).toEqual({ template: "SURVEY_REPORT" }),
    );
    expect(await screen.findByText(/Laporan survei \(\.docx\) · .* · Dian/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Unduh" })).toBeInTheDocument();
  });
});

describe("Verifikasi QR (publik)", () => {
  it("tanpa login: dokumen asli menampilkan penanda tangan dan sidik", async () => {
    const calls = mockApi((c) =>
      c.url === "/verify/work-completions/00000000-0000-4000-8000-0000000000c1"
        ? { data: { completion_id: "c-1", order_number: "PHR-01", client_name: "PHR", project_title: "CCTV",
                    leader_signer_name: "Agus", leader_signed_at: "2026-10-20T02:00:00Z", pm_signer_name: "Dian",
                    pm_signed_at: "2026-10-20T08:00:00Z", signature_hash: HASH, intact: true } }
        : undefined,
    );
    renderRoute(`/verify/work-completion/00000000-0000-4000-8000-0000000000c1?h=${HASH}`, { role: null });
    expect(await screen.findByText("Asli & tidak berubah")).toBeInTheDocument();
    expect(screen.getByText(/Agus/)).toBeInTheDocument();
    expect(calls[0]!.params).toEqual({ h: HASH });
  });

  it("kode verifikasi salah: tidak memanggil API dan menyatakan tidak terverifikasi", async () => {
    const calls = mockApi(() => undefined);
    renderRoute("/verify/work-completion/00000000-0000-4000-8000-0000000000c1?h=bukan-hash", { role: null });
    expect(await screen.findByText("Tidak terverifikasi")).toBeInTheDocument();
    expect(calls.some((c) => c.url.startsWith("/verify"))).toBe(false);
  });
});
