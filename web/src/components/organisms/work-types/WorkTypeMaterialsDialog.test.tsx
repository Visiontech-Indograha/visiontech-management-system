import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { WorkTypeMaterialsDialog } from "./WorkTypeMaterialsDialog";
import { mockApi, apiError } from "@/test/utils";
import type { DefaultMaterial, WorkType } from "@/services/workTypeService";

const mockWorkType: WorkType = {
  id: "wt-01",
  name: "Penyambungan Kabel FO",
  kind: "WORK",
  unit_measure: "titik",
  division_id: "div-01",
  division_name: "Fiber Optic",
  description: "Splicing kabel FO",
  is_active: true,
  photos: [],
  default_materials: [],
};

const mockMaterial: DefaultMaterial = {
  default_material_id: "mat-01",
  work_type_id: "wt-01",
  material_code: "MC-01",
  material_name: "Kabel Dropcore 1 Core",
  default_qty: 50,
  unit: "meter",
  category: "Kabel dan Aksesoris",
  description: "Kabel drop optic 1 core",
  sort_order: 0,
};

function renderDialog(onClose = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <WorkTypeMaterialsDialog workType={mockWorkType} onClose={onClose} />
    </QueryClientProvider>,
  );
  return { onClose };
}

describe("WorkTypeMaterialsDialog - Konfirmasi Hapus Material Default (U-10)", () => {
  it("klik tombol Hapus membuka ConfirmDialog dengan nama objek dan akibatnya", async () => {
    mockApi((c) => {
      if (c.url === "/work-types/wt-01/materials" && c.method === "get") {
        return { data: [mockMaterial] };
      }
    });

    renderDialog();

    expect(await screen.findByText("Kabel Dropcore 1 Core")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Hapus Kabel Dropcore 1 Core" }));

    const dialog = await screen.findByRole("dialog", { name: "Hapus material default" });
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText(/Hapus material Kabel Dropcore 1 Core dari jenis pekerjaan ini\? Order baru tidak akan menyertakan material ini secara otomatis\./)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Hapus" })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Batal" })).toBeInTheDocument();
  });

  it("klik Batal menutup ConfirmDialog tanpa memanggil API delete", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-types/wt-01/materials" && c.method === "get") {
        return { data: [mockMaterial] };
      }
    });

    renderDialog();

    expect(await screen.findByText("Kabel Dropcore 1 Core")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Hapus Kabel Dropcore 1 Core" }));

    const dialog = await screen.findByRole("dialog", { name: "Hapus material default" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Batal" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Hapus material default" })).toBeNull();
    });
    expect(calls.some((c) => c.method === "delete")).toBe(false);
  });

  it("konfirmasi Hapus memanggil API delete dan menutup dialog konfirmasi setelah sukses", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-types/wt-01/materials" && c.method === "get") {
        return { data: [mockMaterial] };
      }
      if (c.url === "/work-types/materials/mat-01" && c.method === "delete") {
        return { status: 200, data: { message: "Material berhasil dihapus." } };
      }
    });

    renderDialog();

    expect(await screen.findByText("Kabel Dropcore 1 Core")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Hapus Kabel Dropcore 1 Core" }));

    const dialog = await screen.findByRole("dialog", { name: "Hapus material default" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Hapus" }));

    await waitFor(() => {
      expect(calls.some((c) => c.method === "delete" && c.url === "/work-types/materials/mat-01")).toBe(true);
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Hapus material default" })).toBeNull();
    });
  });

  it("galat server menampilkan pesan errorMessage", async () => {
    mockApi((c) => {
      if (c.url === "/work-types/wt-01/materials" && c.method === "get") {
        return { data: [mockMaterial] };
      }
      if (c.url === "/work-types/materials/mat-01" && c.method === "delete") {
        return apiError(409, "MATERIAL_IN_USE", "Material standar masih terikat pada template aktif dan belum bisa dihapus.");
      }
    });

    renderDialog();

    expect(await screen.findByText("Kabel Dropcore 1 Core")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Hapus Kabel Dropcore 1 Core" }));

    const dialog = await screen.findByRole("dialog", { name: "Hapus material default" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Hapus" }));

    expect(await within(dialog).findByText("Material standar masih terikat pada template aktif dan belum bisa dihapus.")).toBeInTheDocument();
  });
});
