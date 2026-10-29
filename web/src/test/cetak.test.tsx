import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TeamWeekButton } from "@/components/organisms/work-plans/DailyWeekToolbar";
import { WorkCompletionExportPanel } from "@/components/organisms/work-completions/WorkCompletionExportPanel";
import { useExportDailyReport } from "@/services/exportService";
import { mockApi } from "./utils";

/** Dokumen cetak: surat tugas order, laporan mingguan tim (.pptx), laporan harian per jadwal. */

function withClient(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const TEAM_A = { team_id: "t-a", name: "Tim MEP", division_id: "d-1", leader_employee_id: "e-1", leader_name: "Agus" };
const TEAM_B = { team_id: "t-b", name: "Tim CCTV", division_id: "d-1", leader_employee_id: "e-2", leader_name: "Dian" };

describe("Surat tugas order (ORDER_SHEET)", () => {
  beforeEach(() => {
    window.URL.createObjectURL = vi.fn(() => "blob:x");
    window.URL.revokeObjectURL = vi.fn();
  });

  it("tersedia sebelum PM mengesahkan order (tanpa tanda tangan)", () => {
    mockApi((c) => (c.url === "/exports/work-completions/c-1" ? { data: [] } : undefined));
    withClient(<WorkCompletionExportPanel completionId="c-1" signed={false} />);
    expect(screen.getByRole("button", { name: /Surat tugas \/ lembar order \(\.docx\)/ })).toBeEnabled();
  });
});

describe("Laporan mingguan tim (.pptx)", () => {
  beforeEach(() => {
    window.URL.createObjectURL = vi.fn(() => "blob:x");
    window.URL.revokeObjectURL = vi.fn();
  });

  it("dengan satu tim: langsung mengirim team_id dan Senin minggu yang tampil", async () => {
    const calls = mockApi((c) => (c.method === "post" ? { data: new Blob(["pptx"]) } : undefined));
    withClient(<TeamWeekButton teams={[TEAM_A]} start="2026-11-02" />);
    fireEvent.click(screen.getByRole("button", { name: "Laporan mingguan tim (.pptx)" }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "post")).toEqual(
        expect.objectContaining({ url: "/exports/team-week", data: { team_id: "t-a", start_date: "2026-11-02" } }),
      ),
    );
  });

  it("dengan dua tim: tombol nonaktif sampai tim dipilih", async () => {
    const calls = mockApi((c) => (c.method === "post" ? { data: new Blob(["pptx"]) } : undefined));
    withClient(<TeamWeekButton teams={[TEAM_A, TEAM_B]} start="2026-11-02" />);
    const button = screen.getByRole("button", { name: "Laporan mingguan tim (.pptx)" });
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Tim"), { target: { value: "t-b" } });
    expect(button).toBeEnabled();
    fireEvent.click(button);
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/exports/team-week")).toBe(true));
    expect(calls.find((c) => c.method === "post")?.data).toEqual({ team_id: "t-b", start_date: "2026-11-02" });
  });
});

describe("Laporan harian per jadwal (.docx)", () => {
  beforeEach(() => {
    window.URL.createObjectURL = vi.fn(() => "blob:x");
    window.URL.revokeObjectURL = vi.fn();
  });

  it("mengirim daily_plan_id ke /exports/daily-report", async () => {
    const calls = mockApi((c) => (c.method === "post" ? { data: new Blob(["docx"]) } : undefined));
    function Probe() {
      const exporter = useExportDailyReport();
      return <button onClick={() => exporter.mutate({ daily_plan_id: "d-1" })}>cetak</button>;
    }
    withClient(<Probe />);
    fireEvent.click(screen.getByRole("button", { name: "cetak" }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "post")).toEqual(
        expect.objectContaining({ url: "/exports/daily-report", data: { daily_plan_id: "d-1" } }),
      ),
    );
  });
});
