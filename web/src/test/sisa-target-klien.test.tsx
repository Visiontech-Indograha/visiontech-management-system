import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { DailyItemsPanel } from "@/components/organisms/work-plans/DailyItemsPanel";
import { ClientFormDialog } from "@/components/organisms/clients/ClientFormDialog";
import { mockApi, apiError } from "./utils";

/** Sisa target order di form item jadwal, dan tombol "Pakai klien yang sudah ada" saat nama klien sudah ada. */

function renderWithProviders(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>,
  );
}

const detail = {
  daily_plan_id: "p1", division_id: "d1", division_name: "Sipil", team_id: "t1", team_name: "Tim Alpha",
  status: "DRAFT", items: [], attachment_file_ids: [], work_date: "2026-11-02", site_name: "Gardu",
} as never;

const formOptions = {
  divisions: [{ division_id: "d1", name: "Sipil" }],
  teams: [],
  orders: [{ completion_id: "o1", order_number: "PO-1", client_name: "PT A", project_title: "Pasang CCTV", division_id: "d1" }],
};

const schedule = {
  total_target_unit: 10, completed_target_unit: 0, scheduled_target_qty: 7, unscheduled_target_qty: 3, plans: [],
};

describe("form item jadwal: sisa target order", () => {
  it("target di atas sisa memunculkan peringatan; target dalam sisa tidak", async () => {
    mockApi((c) => {
      if (c.url === "/work-plans/form-options") return { data: formOptions };
      if (c.url === "/work-plans/orders/o1/schedule") return { data: schedule };
      if (c.url === "/work-types") return { data: [] };
    });
    renderWithProviders(<DailyItemsPanel detail={detail} loading={false} canPlan />);
    fireEvent.click(await screen.findByRole("button", { name: "Tambah pekerjaan" }));

    fireEvent.change(await screen.findByLabelText("Pekerjaan Klien / Order SPK (opsional)"), { target: { value: "o1" } });
    expect(await screen.findByText(/sisa belum dijadwalkan 3/)).toBeInTheDocument();

    const target = screen.getByLabelText("Target volume");
    fireEvent.change(target, { target: { value: "5" } });
    expect(screen.getByRole("alert")).toHaveTextContent(/Alokasi melebihi sisa target order \(2 di atas sisa\)/);

    fireEvent.change(target, { target: { value: "2" } });
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  });
});

describe("master klien: nama sudah ada", () => {
  it("409 CLIENT_EXISTS menampilkan 'Pakai klien yang sudah ada' dan memakai id klien yang ada", async () => {
    const onUseExisting = vi.fn();
    mockApi((c) => {
      if (c.url === "/clients" && c.method === "post") {
        return apiError(409, "CLIENT_EXISTS", 'Klien "PT Gardu" sudah ada. Pilih klien yang sudah ada.',
          { client_id: "c-lama", name: "PT Gardu" });
      }
    });
    renderWithProviders(<ClientFormDialog client={null} onClose={() => {}} onUseExisting={onUseExisting} />);
    fireEvent.change(screen.getByLabelText("Kode Klien"), { target: { value: "PLN-2" } });
    fireEvent.change(screen.getByLabelText(/Nama Perusahaan Klien/), { target: { value: "PT Gardu" } });
    fireEvent.click(screen.getByRole("button", { name: "Tambah Klien" }));

    const use = await screen.findByRole("button", { name: "Pakai klien yang sudah ada" });
    fireEvent.click(use);
    expect(onUseExisting).toHaveBeenCalledWith("c-lama");
  });

  it("tanpa 409 CLIENT_EXISTS tombol tidak tampil", async () => {
    mockApi((c) => {
      if (c.url === "/clients" && c.method === "post") {
        return apiError(409, "CLIENT_CODE_TAKEN", "Kode klien sudah dipakai.");
      }
    });
    renderWithProviders(<ClientFormDialog client={null} onClose={() => {}} onUseExisting={() => {}} />);
    fireEvent.change(screen.getByLabelText("Kode Klien"), { target: { value: "PLN-3" } });
    fireEvent.change(screen.getByLabelText(/Nama Perusahaan Klien/), { target: { value: "PT Lain" } });
    fireEvent.click(screen.getByRole("button", { name: "Tambah Klien" }));
    await screen.findByText("Kode klien sudah dipakai.");
    expect(screen.queryByRole("button", { name: "Pakai klien yang sudah ada" })).not.toBeInTheDocument();
  });
});
