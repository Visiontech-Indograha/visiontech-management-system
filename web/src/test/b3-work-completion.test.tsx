import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { WorkCompletionFormDialog } from "@/components/organisms/work-completions/WorkCompletionFormDialog";
import { mockMe } from "@/app/mockSession";
import { useSession } from "@/stores/sessionStore";
import { apiError, mockApi } from "./utils";

const clients = [
  { client_id: "c1", client_code: "PLN", name: "PT Gardu Nusantara", is_active: true },
  { client_id: "c2", client_code: "TLK", name: "Telkom Regional", is_active: true },
];

function renderForm() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <WorkCompletionFormDialog onClose={() => {}} />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("formulir pekerjaan klien (W12)", () => {
  beforeEach(() => {
    useSession.setState({ me: { ...mockMe("PM")!, division_id: "d1" }, ready: true });
  });

  it("kolom cari klien menyaring daftar klien master", async () => {
    mockApi((c) => {
      if (c.url === "/clients") return { data: clients };
      if (c.url === "/projects") return { data: [] };
    });
    renderForm();
    const select = (await screen.findByLabelText("Pilih Klien Master")) as HTMLSelectElement;
    await waitFor(() => expect(select.options.length).toBe(3));
    fireEvent.change(screen.getByLabelText("Cari klien"), { target: { value: "telkom" } });
    expect(Array.from(select.options).map((o) => o.textContent)).toEqual(["-- Pilih Klien Terdaftar --", "TLK - Telkom Regional"]);
  });

  it("galat dari kirim tetap tampil sampai kolom diubah, lalu hilang", async () => {
    mockApi((c) => {
      if (c.url === "/clients") return { data: clients };
      if (c.url === "/projects") return { data: [] };
      if (c.url === "/work-completions" && c.method === "post") return apiError(500, "ERR", "gagal");
    });
    renderForm();
    const select = (await screen.findByLabelText("Pilih Klien Master")) as HTMLSelectElement;
    await waitFor(() => expect(select.options.length).toBe(3));
    fireEvent.change(select, { target: { value: "c1" } });
    fireEvent.change(screen.getByLabelText("Judul Pekerjaan / Proyek"), { target: { value: "Gardu Timur" } });
    fireEvent.click(screen.getByRole("button", { name: /simpan/i }));
    expect(await screen.findByText(/Gagal membuat order proyek klien/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Judul Pekerjaan / Proyek"), { target: { value: "Gardu Timur 2" } });
    await waitFor(() => expect(screen.queryByText(/Gagal membuat order proyek klien/)).toBeNull());
  });
});
