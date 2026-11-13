import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider, type UseQueryResult } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { Perangkat } from "@/services/hikvisionService";
import { DeviceList } from "./DeviceList";

vi.mock("./DeviceStatusLine", () => ({ DeviceStatusLine: () => <div>status</div> }));

const actions = { onAdd: vi.fn(), onEdit: vi.fn(), onLink: vi.fn(), onMappings: vi.fn(), onMode: vi.fn(), onRemove: vi.fn() };
const q = (o: Partial<UseQueryResult<Perangkat[]>>) => o as UseQueryResult<Perangkat[]>;
const wrap = (ui: React.ReactElement) => render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);

const device = {
  device_id: "1", office_id: "o", office_name: "Pekanbaru", name: "Pintu depan", ip_address: "10.0.0.5", http_port: 80,
  serial_no: "S1", model: null, mode: "SHADOW", aktif: true, catatan: null, create_at: "", update_at: "",
} as Perangkat;

describe("DeviceList", () => {
  it("kosong: ada ajakan tambah mesin", () => {
    wrap(<DeviceList devices={q({ isPending: false, isError: false, data: [] })} actions={actions} />);
    expect(screen.getByRole("button", { name: "Tambah mesin" })).toBeInTheDocument();
  });
  it("galat: ada tombol Coba lagi", () => {
    wrap(<DeviceList devices={q({ isPending: false, isError: true, refetch: vi.fn() as never })} actions={actions} />);
    expect(screen.getByRole("button", { name: "Coba lagi" })).toBeInTheDocument();
  });
  it("berhasil: mode memakai label awam", () => {
    wrap(<DeviceList devices={q({ isPending: false, isError: false, data: [device] })} actions={actions} />);
    expect(screen.getByText("Mode Bayangan")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Jadikan Aktif" })).toBeInTheDocument();
  });
});
