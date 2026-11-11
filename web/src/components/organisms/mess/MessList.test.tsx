import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MessList } from "./MessList";
import type { MessStay } from "@/services/messService";

const stay = (start: string): MessStay =>
  ({
    mess_stay_id: "s1", mess_name: "Mess A", city: "Bali", address: "Jl X", employee_id: "e1",
    employee_name: "Budi", stay_start_date: start, stay_end_date: "2999-12-31", status: "APPROVED",
  }) as MessStay;

const view = (s: MessStay, canAdd: boolean) => {
  const onCancel = vi.fn();
  const stays = { isPending: false, isError: false, data: { items: [s], total: 1 } } as never;
  const controls = { size: 20, page: 1, input: "", search: "", active: false, setInput: vi.fn(), setPage: vi.fn(), reset: vi.fn() } as never;
  render(<QueryClientProvider client={new QueryClient()}><MessList controls={controls} stays={stays} canAdd={canAdd} onAdd={vi.fn()} onCheckout={vi.fn()} onCancel={onCancel} /></QueryClientProvider>);
  return onCancel;
};

describe("MessList batalkan hunian", () => {
  it("tampil untuk hunian belum dimulai dan memanggil onCancel setelah konfirmasi", () => {
    const onCancel = view(stay("2999-01-01"), true);
    fireEvent.click(screen.getByRole("button", { name: "Batalkan hunian" }));
    const buttons = screen.getAllByRole("button", { name: "Batalkan hunian" });
    fireEvent.click(buttons[buttons.length - 1]);
    expect(onCancel).toHaveBeenCalled();
  });
  it("tidak tampil bila sudah berjalan", () => {
    view(stay("2000-01-01"), true);
    expect(screen.queryByRole("button", { name: "Batalkan hunian" })).toBeNull();
  });
  it("tidak tampil tanpa izin", () => {
    view(stay("2999-01-01"), false);
    expect(screen.queryByRole("button", { name: "Batalkan hunian" })).toBeNull();
  });
});
