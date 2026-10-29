import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { ProjectDeleteDialog } from "@/components/organisms/projects/ProjectDeleteDialog";
import type { Project } from "@/services/projectService";
import { apiError, mockApi } from "./utils";

const project = (over: Partial<Project> = {}) =>
  ({
    project_id: "p1", project_title: "Gardu Induk Timur", spk_number: "SPK-01",
    daily_plan_count: 0, order_count: 0, ...over,
  }) as Project;

function renderDialog(p: Project, onClose = () => {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ProjectDeleteDialog project={p} onClose={onClose} />
    </QueryClientProvider>,
  );
}

describe("ProjectDeleteDialog", () => {
  it("memakai satu istilah 'Arsipkan' dan menjelaskan dampaknya", () => {
    renderDialog(project());
    expect(screen.getByRole("heading", { name: "Arsipkan proyek" })).toBeTruthy();
    expect(screen.queryByText(/Hapus \/ Batalkan/)).toBeNull();
    expect(screen.getByText(/disembunyikan dari daftar proyek/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ya, arsipkan" })).toBeTruthy();
  });

  it("proyek yang sudah punya jadwal atau order tidak bisa diarsipkan dan tombol konfirmasi tidak ditampilkan", () => {
    renderDialog(project({ daily_plan_count: 2, order_count: 1 }));
    expect(screen.getByText(/tidak dapat diarsipkan/)).toBeTruthy();
    expect(screen.getByText(/2 jadwal harian/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Ya, arsipkan" })).toBeNull();
  });

  it("galat dari API ditampilkan apa adanya", async () => {
    mockApi((c) => {
      if (c.method === "delete") return apiError(409, "PROJECT_IN_USE", "Proyek sudah punya jadwal atau order. Batalkan lewat status saja.");
    });
    renderDialog(project());
    fireEvent.click(screen.getByRole("button", { name: "Ya, arsipkan" }));
    expect(await screen.findByText(/Batalkan lewat status saja/)).toBeTruthy();
    await waitFor(() => expect(screen.getByRole("button", { name: "Ya, arsipkan" })).toBeTruthy());
  });
});
