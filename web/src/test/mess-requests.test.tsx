import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

const request = {
  mess_stay_id: "s1", mess_id: "m1", mess_name: "Mess Duri", city: "Duri", address: "Jl. Uji 1",
  employee_id: "e1", employee_name: "Uji Anggota", employee_no: "N1", stay_start_date: "2026-11-01",
  stay_end_date: "2026-11-05", status: "REQUESTED", request_note: "Proyek CCTV", create_at: "2026-10-27T10:00:00Z",
};
const place = { mess_id: "m1", mess_name: "Mess Duri", city: "Duri", address: "Jl. Uji 1", capacity: 2, occupied: 1 };

const handler = (c: { url?: string; method?: string; params?: { status?: string } }) => {
  if (c.url === "/mess" && c.method === "get") return { data: c.params?.status === "REQUESTED" ? [request] : [] };
  if (c.url === "/mess/places") return { data: [place] };
};

describe("Mess: permintaan dan daftar mess", () => {
  it("peninjau melihat tab Permintaan dengan jumlah menunggu dan wajib alasan saat menolak", async () => {
    mockApi(handler);
    renderRoute("/mess", { role: "ADMIN" });
    const tab = await screen.findByRole("tab", { name: /Permintaan \(1\)/ });
    await userEvent.click(tab);
    expect(await screen.findByText("Uji Anggota")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Tolak Uji Anggota" }));
    await userEvent.click(await screen.findByRole("button", { name: "Tolak pengajuan" }));
    expect(await screen.findByText("Alasan penolakan wajib diisi.")).toBeInTheDocument();
  });

  it("daftar mess menampilkan keterisian", async () => {
    mockApi(handler);
    renderRoute("/mess", { role: "ADMIN" });
    await userEvent.click(await screen.findByRole("tab", { name: "Daftar Mess" }));
    expect(await screen.findByText(/Terisi hari ini: 1 dari 2 orang/)).toBeInTheDocument();
  });
});
