import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { BandingBaris, BandingBayangan } from "@/services/hikvisionService";
import { BandingTable } from "./BandingTable";

const row = {
  employee_id: "e1", employee_name: "Budi", tgl: "2026-11-10", pertama: "2026-11-10T00:58:00Z", terakhir: "2026-11-10T10:00:00Z",
  jumlah: 2, clock_in_at: "2026-11-10T01:10:00Z", clock_out_at: null, selisih_masuk_menit: -12, selisih_pulang_menit: null, status: "waktu_berbeda",
} as BandingBaris;
const data = { items: [row], tak_terpetakan: 3, terpotong: true } as BandingBayangan;
const props = { rows: [row], total: 1, page: 1, shownPage: 1, lastPage: 1, onPageChange: vi.fn(), filtered: false };
const q = (o: object) => ({ isPending: false, isError: false, refetch: vi.fn(), ...o });

describe("BandingTable", () => {
  it("memuat: tabel belum tampil", () => {
    render(<BandingTable {...props} query={q({ isPending: true })} />);
    expect(screen.queryByRole("table")).toBeNull();
  });
  it("galat: ada tombol Coba lagi", () => {
    render(<BandingTable {...props} query={q({ isError: true })} />);
    expect(screen.getByRole("button", { name: "Coba lagi" })).toBeInTheDocument();
  });
  it("kosong: ada penjelasan", () => {
    render(<BandingTable {...props} rows={[]} total={0} query={q({ data })} />);
    expect(screen.getByText(/Belum ada catatan dari mesin/)).toBeInTheDocument();
  });
  it("hanya di aplikasi: waktu mesin kosong tidak membuat galat", () => {
    const r = { ...row, pertama: null, terakhir: null, jumlah: 0, status: "hanya_aplikasi" } as BandingBaris;
    render(<BandingTable {...props} rows={[r]} query={q({ data })} />);
    expect(screen.getByText("Hanya di aplikasi")).toBeInTheDocument();
    expect(screen.getByText("Tidak ada di mesin")).toBeInTheDocument();
  });
  it("sebagian + berhasil: peringatan dan status awam", () => {
    render(<BandingTable {...props} query={q({ data })} />);
    expect(screen.getByText(/3 catatan mesin belum dicocokkan/)).toBeInTheDocument();
    expect(screen.getByText(/Data terlalu banyak/)).toBeInTheDocument();
    expect(screen.getByText("Waktu berbeda")).toBeInTheDocument();
    expect(screen.getByText("Budi")).toBeInTheDocument();
  });
});
