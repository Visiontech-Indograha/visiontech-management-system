import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { WorkCompletionFormDialog } from "@/components/organisms/work-completions/WorkCompletionFormDialog";
import { ClientFormDialog } from "@/components/organisms/clients/ClientFormDialog";
import { WorkCompletionList } from "@/components/organisms/work-completions/WorkCompletionList";
import { mockMe } from "@/app/mockSession";
import { useSession } from "@/stores/sessionStore";
import { mockApi } from "./utils";

/** Temuan uji manual web (pm1): halaman Pekerjaan klien — SPK kosong, ubah, lintang/bujur, nama klien. */

const clients = [{ client_id: "c1", client_code: "PLN", name: "PT Gardu Nusantara", is_active: true }];

function renderWithProviders(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>,
  );
}

const order = {
  completion_id: "wc1", division_id: "d1", division_name: "Sipil", client_id: null, client_name: "PT Gardu Nusantara",
  project_title: "Pasang CCTV", order_number: "PO-1", total_target_unit: 10, completed_target_unit: 0, phases: [],
  progress_pct: 0, unit_measure: "Unit", order_status: "ONGOING", priority_level: "NORMAL", acc_status: "PENDING",
  site_address: null, site_lat: null, site_lng: null, summary_notes: null, revisions: 0,
};

describe("pekerjaan klien: SPK kosong", () => {
  beforeEach(() => {
    useSession.setState({ me: { ...mockMe("PM")!, division_id: "d1" }, ready: true });
  });

  it("klien tanpa SPK menampilkan tautan 'Buat SPK untuk klien ini' ke Master Proyek dengan klien itu", async () => {
    mockApi((c) => {
      if (c.url === "/clients") return { data: clients };
      if (c.url === "/projects") return { data: [] };
    });
    renderWithProviders(<WorkCompletionFormDialog onClose={() => {}} />);
    const select = (await screen.findByLabelText("Pilih Klien Master")) as HTMLSelectElement;
    await waitFor(() => expect(select.options.length).toBe(2));
    fireEvent.change(select, { target: { value: "c1" } });
    expect(await screen.findByText(/Klien ini belum punya SPK aktif/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Buat SPK untuk klien ini" })).toHaveAttribute("href", "/projects?client_id=c1");
  });
});

describe("pekerjaan klien: lintang dan bujur", () => {
  beforeEach(() => {
    useSession.setState({ me: { ...mockMe("PM")!, division_id: "d1" }, ready: true });
  });

  it("lintang di luar -90..90 ditolak di web dan tidak dikirim", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/clients") return { data: [] };
      if (c.url === "/projects") return { data: [] };
      if (c.url === "/work-completions" && c.method === "post") return { data: order };
    });
    renderWithProviders(<WorkCompletionFormDialog onClose={() => {}} />);
    fireEvent.change(await screen.findByLabelText("Nama Klien / Perusahaan"), { target: { value: "PT Gardu" } });
    fireEvent.change(screen.getByLabelText("Judul Pekerjaan / Proyek"), { target: { value: "Pasang CCTV" } });
    fireEvent.change(screen.getByLabelText("Latitude Lokasi (Opsional)"), { target: { value: "95" } });
    fireEvent.change(screen.getByLabelText("Longitude Lokasi (Opsional)"), { target: { value: "106.8" } });
    fireEvent.click(screen.getByRole("button", { name: /simpan/i }));
    expect(await screen.findByText(/Lintang tidak valid\. Harus antara -90 dan 90/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post" && c.url === "/work-completions")).toBe(false);
  });
});

describe("pekerjaan klien: nama klien", () => {
  beforeEach(() => {
    useSession.setState({ me: { ...mockMe("PM")!, division_id: "d1" }, ready: true });
  });

  it.each([
    ["tag HTML", "<b>PT Gardu</b>", /tidak boleh memuat tanda < atau >/],
    ["emoji", "PT Gardu 🚀", /tidak boleh memuat emoji/],
  ])("nama dengan %s ditolak dan tidak dikirim", async (_label, name, pesan) => {
    const calls = mockApi((c) => {
      if (c.url === "/clients") return { data: [] };
      if (c.url === "/projects") return { data: [] };
    });
    renderWithProviders(<WorkCompletionFormDialog onClose={() => {}} />);
    fireEvent.change(await screen.findByLabelText("Nama Klien / Perusahaan"), { target: { value: name } });
    fireEvent.change(screen.getByLabelText("Judul Pekerjaan / Proyek"), { target: { value: "Pasang CCTV" } });
    fireEvent.click(screen.getByRole("button", { name: /simpan/i }));
    expect(await screen.findByText(pesan)).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post" && c.url === "/work-completions")).toBe(false);
  });
});

describe("pekerjaan klien: ubah", () => {
  beforeEach(() => {
    useSession.setState({ me: { ...mockMe("PM")!, division_id: "d1" }, ready: true });
  });

  it("tombol Ubah membuka formulir terisi dan menyimpan dengan PUT", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/clients") return { data: clients };
      if (c.url === "/projects") return { data: [] };
      if (c.url === "/work-completions/wc1" && c.method === "put") return { data: order };
    });
    const query = { data: [order], isPending: false, isError: false, isSuccess: true, refetch: () => {} } as never;
    renderWithProviders(<WorkCompletionList query={query} canManage onAdd={() => {}} />);
    fireEvent.click(await screen.findByRole("button", { name: "Ubah" }));
    const dialog = await screen.findByRole("dialog", { name: "Ubah pekerjaan klien" });
    expect(within(dialog).getByLabelText("Judul Pekerjaan / Proyek")).toHaveValue("Pasang CCTV");
    fireEvent.change(within(dialog).getByLabelText("Judul Pekerjaan / Proyek"), { target: { value: "Pasang CCTV 2" } });
    fireEvent.click(within(dialog).getByRole("button", { name: /simpan/i }));
    await waitFor(() => expect(calls.some((c) => c.method === "put" && c.url === "/work-completions/wc1")).toBe(true));
    expect(calls.find((c) => c.method === "put")?.data).toMatchObject({ project_title: "Pasang CCTV 2", client_name: "PT Gardu Nusantara" });
  });
});

describe("master klien: nama klien", () => {
  it("nama dengan tag HTML ditolak di formulir klien dan tidak dikirim", async () => {
    const calls = mockApi(() => ({ data: {} }));
    renderWithProviders(<ClientFormDialog client={null} onClose={() => {}} />);
    fireEvent.change(screen.getByLabelText(/Nama Perusahaan Klien/), { target: { value: "<img src=x>" } });
    fireEvent.click(screen.getByRole("button", { name: "Tambah Klien" }));
    expect(await screen.findByText(/tidak boleh memuat tanda < atau >/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === "post")).toBe(false);
  });
});
