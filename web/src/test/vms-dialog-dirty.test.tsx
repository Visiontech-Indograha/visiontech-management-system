import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { VmsDialog } from "@/components/molecules/VmsDialog";

describe("VmsDialog dirty", () => {
  it("meminta konfirmasi bila formulir berubah, lalu menutup bila dikonfirmasi", async () => {
    const onClose = vi.fn();
    render(
      <VmsDialog open title="Uji" onClose={onClose} dirty>
        isi
      </VmsDialog>,
    );
    await userEvent.keyboard("{Escape}");
    expect(await screen.findByText(/Perubahan belum disimpan/)).toBeTruthy();
    expect(onClose).not.toHaveBeenCalled();
    await userEvent.click(screen.getByText("Tutup tanpa menyimpan"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("langsung menutup bila tidak ada perubahan", async () => {
    const onClose = vi.fn();
    render(
      <VmsDialog open title="Uji" onClose={onClose}>
        isi
      </VmsDialog>,
    );
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
