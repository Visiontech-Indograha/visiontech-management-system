import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AssetFormDialog } from "@/components/organisms/assets/AssetFormDialog";
import { AttendanceFormDialog } from "@/components/organisms/attendance/AttendanceFormDialog";
import { WorkCompletionFormDialog } from "@/components/organisms/work-completions/WorkCompletionFormDialog";
import { MemoryRouter } from "react-router-dom";
import { mockMe } from "@/app/mockSession";
import { useSession } from "@/stores/sessionStore";
import { mockApi } from "./utils";

/** Temuan uji manual web (pm1) — satu kelompok uji per temuan. */

function withQuery(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>,
  );
}

const DISCARD_ALERT = /Perubahan belum disimpan/;

describe("1. formulir terisi: Batal, klik luar, Esc meminta konfirmasi", () => {
  beforeEach(() => {
    useSession.setState({ me: { ...mockMe("PM")!, division_id: "d1" }, ready: true });
  });

  it("Batal pada AssetFormDialog yang sudah diisi meminta konfirmasi, tidak langsung menutup", () => {
    const onClose = vi.fn();
    withQuery(
      <AssetFormDialog title="Tambah alat" submitting={false} formError={null} onClose={onClose} onSubmit={() => {}}>
        <input aria-label="Nama alat" />
      </AssetFormDialog>,
    );
    fireEvent.change(screen.getByLabelText("Nama alat"), { target: { value: "Bor" } });
    fireEvent.click(screen.getByRole("button", { name: "Batal" }));
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(DISCARD_ALERT);
    fireEvent.click(screen.getByRole("button", { name: "Tutup tanpa menyimpan" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("Batal pada AttendanceFormDialog yang sudah diisi meminta konfirmasi", () => {
    const onClose = vi.fn();
    withQuery(
      <AttendanceFormDialog title="Koreksi absen" submitLabel="Simpan" submitting={false} formError={null} onClose={onClose} onSubmit={() => {}}>
        <input aria-label="Alasan" />
      </AttendanceFormDialog>,
    );
    fireEvent.change(screen.getByLabelText("Alasan"), { target: { value: "Lupa absen" } });
    fireEvent.click(screen.getByRole("button", { name: "Batal" }));
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(DISCARD_ALERT);
  });

  it("Batal pada formulir kosong tetap langsung menutup", () => {
    const onClose = vi.fn();
    withQuery(
      <AssetFormDialog title="Tambah alat" submitting={false} formError={null} onClose={onClose} onSubmit={() => {}}>
        <input aria-label="Nama alat" />
      </AssetFormDialog>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Batal" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("Esc pada Pekerjaan klien yang sudah terisi meminta konfirmasi", async () => {
    const onClose = vi.fn();
    mockApi((c) => {
      if (c.url === "/clients") return { data: [] };
      if (c.url === "/projects") return { data: [] };
    });
    withQuery(<WorkCompletionFormDialog onClose={onClose} />);
    fireEvent.change(await screen.findByLabelText("Judul Pekerjaan / Proyek"), { target: { value: "Gardu Timur" } });
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(DISCARD_ALERT));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("Batal pada Pekerjaan klien yang sudah terisi meminta konfirmasi", async () => {
    const onClose = vi.fn();
    mockApi((c) => {
      if (c.url === "/clients") return { data: [] };
      if (c.url === "/projects") return { data: [] };
    });
    withQuery(<WorkCompletionFormDialog onClose={onClose} />);
    fireEvent.change(await screen.findByLabelText("Judul Pekerjaan / Proyek"), { target: { value: "Gardu Timur" } });
    fireEvent.click(screen.getByRole("button", { name: "Batal" }));
    expect(onClose).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent(DISCARD_ALERT);
  });
});
