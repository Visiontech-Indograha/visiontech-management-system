import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

/** Form tempatkan karyawan di mess: pilih tim, dan peringatan kapasitas per tanggal (kapasitas = 2). */
const place = { mess_id: "m1", mess_name: "Mess Duri", city: "Duri", address: "Jl. Uji 1", capacity: 2, occupied: 0 };
const approved = (id: string, start: string, end: string) => ({
  mess_stay_id: id, mess_id: "m1", mess_name: "Mess Duri", city: "Duri", address: "Jl. Uji 1", employee_id: `e-${id}`,
  employee_name: `Penghuni ${id}`, employee_no: id, stay_start_date: start, stay_end_date: end, status: "APPROVED",
  create_at: "2026-10-27T10:00:00Z",
});

async function openForm(stays: unknown[]) {
  mockApi((c) => {
    if (c.url === "/mess/places") return { data: [place] };
    if (c.url === "/mess" && c.method === "get") return { data: c.params?.status === "APPROVED" ? stays : [] };
    if (c.url === "/mess" && c.method === "post") return { status: 201, data: {} };
    if (c.url === "/employees") return { data: { items: [{ employee_id: "e1", full_name: "Doni", employee_no: "VT-08", join_date: "2024-01-01", offboarding_status: "active" }], total: 1, page: 1, size: 100 } };
    if (c.url === "/teams") return { data: [{ team_id: "tm1", name: "Tim Alfa" }] };
  });
  renderRoute("/mess", { role: "ADMIN" });
  await userEvent.click(await screen.findByRole("button", { name: "Tempatkan Karyawan" }));
  return screen.findByRole("dialog", { name: "Tempatkan Karyawan di Mess" });
}


describe("Hunian mess: tim dan kapasitas per tanggal", () => {
  it("rentang yang sudah penuh pada suatu tanggal menampilkan peringatan dengan tanggal itu", async () => {
    const dialog = await openForm([
      approved("a", "2026-11-01", "2026-11-02"),
      approved("b", "2026-11-02", "2026-11-03"),
    ]);
    fireEvent.change(within(dialog).getByLabelText("Mess"), { target: { value: "m1" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal Mulai Inap"), { target: { value: "2026-11-01" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal Selesai Inap"), { target: { value: "2026-11-03" } });
    const alert = await within(dialog).findByRole("alert");
    expect(alert).toHaveTextContent("Mess penuh pada 02-11-2026");
    expect(alert).not.toHaveTextContent("01-11-2026");
  });

  it("rentang yang masih muat tidak menampilkan peringatan", async () => {
    const dialog = await openForm([approved("a", "2026-11-01", "2026-11-02")]);
    fireEvent.change(within(dialog).getByLabelText("Mess"), { target: { value: "m1" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal Mulai Inap"), { target: { value: "2026-11-01" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal Selesai Inap"), { target: { value: "2026-11-02" } });
    await waitFor(() => expect(within(dialog).queryByRole("alert")).toBeNull());
  });

  it("tim yang dipilih ikut dikirim sebagai team_id", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/mess/places") return { data: [place] };
      if (c.url === "/mess" && c.method === "get") return { data: [] };
      if (c.url === "/mess" && c.method === "post") return { status: 201, data: {} };
      if (c.url === "/employees") return { data: { items: [{ employee_id: "e1", full_name: "Doni", employee_no: "VT-08", join_date: "2024-01-01", offboarding_status: "active" }], total: 1, page: 1, size: 100 } };
      if (c.url === "/teams") return { data: [{ team_id: "00000000-0000-0000-0000-00000000000a", name: "Tim Alfa" }] };
    });
    renderRoute("/mess", { role: "ADMIN" });
    await userEvent.click(await screen.findByRole("button", { name: "Tempatkan Karyawan" }));
    const dialog = await screen.findByRole("dialog", { name: "Tempatkan Karyawan di Mess" });
    fireEvent.change(within(dialog).getByLabelText("Karyawan yang Menempati"), { target: { value: "e1" } });
    fireEvent.change(within(dialog).getByLabelText("Mess"), { target: { value: "m1" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal Mulai Inap"), { target: { value: "2026-11-01" } });
    fireEvent.change(within(dialog).getByLabelText("Tanggal Selesai Inap"), { target: { value: "2026-11-02" } });
    fireEvent.change(within(dialog).getByLabelText("Tim yang menginap (opsional)"), { target: { value: "00000000-0000-0000-0000-00000000000a" } });
    await userEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post" && c.url === "/mess")).toBe(true));
    expect(calls.find((c) => c.method === "post" && c.url === "/mess")!.data).toMatchObject({
      employee_id: "e1", mess_id: "m1", team_id: "00000000-0000-0000-0000-00000000000a",
    });
  });
});
