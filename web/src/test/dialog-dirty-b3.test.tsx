import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { TeamFormDialog } from "@/components/organisms/teams/TeamFormDialog";
import { mockApi } from "./utils";

function renderTeam(onClose: () => void) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TeamFormDialog onClose={onClose} />
    </QueryClientProvider>,
  );
}

describe("formulir yang berubah meminta konfirmasi sebelum ditutup (W13)", () => {
  it("klik di luar setelah mengetik meminta konfirmasi, tidak langsung menutup", async () => {
    mockApi(() => ({ data: [] }));
    const onClose = vi.fn();
    renderTeam(onClose);
    await userEvent.type(screen.getByLabelText("Nama tim"), "Tim Uji");
    await userEvent.keyboard("{Escape}");
    expect(await screen.findByText(/Perubahan belum disimpan/)).toBeTruthy();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("formulir belum diubah langsung tertutup", async () => {
    mockApi(() => ({ data: [] }));
    const onClose = vi.fn();
    renderTeam(onClose);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
