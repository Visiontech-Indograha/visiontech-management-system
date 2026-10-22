import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi, renderRoute } from "./utils";

const mockUnits = [
  { id: "11111111-2222-3333-4444-555555555555", code: "FTTX", name: "Fiber Optic" },
  { id: "22222222-3333-4444-5555-666666666666", code: "MEP", name: "Mechanical Electrical" },
];

const mockWorkType = {
  id: "wt-01",
  name: "Penyambungan Kabel FO",
  division_id: "11111111-2222-3333-4444-555555555555",
  division_name: "Fiber Optic",
  description: "Penyambungan kabel backbone fiber optic",
  is_active: true,
  photos: [
    {
      id: "slot-01",
      sort_order: 1,
      label: "Foto OTB Sebelum",
      hint: "Foto close up OTB sebelum splicing",
      required: true,
      example_file_id: null,
    },
  ],
};

describe("Jenis Pekerjaan (/work-types)", () => {
  it("menampilkan daftar jenis pekerjaan dengan badge divisi", async () => {
    mockApi((c) => {
      if (c.url === "/work-types") return { data: [mockWorkType] };
      if (c.url === "/divisions") return { data: mockUnits };
    });

    renderRoute("/work-types", { role: "PM" });

    expect(await screen.findByText("Penyambungan Kabel FO")).toBeInTheDocument();
    expect(screen.getByText("Fiber Optic")).toBeInTheDocument();
    expect(screen.getByText("Penyambungan kabel backbone fiber optic")).toBeInTheDocument();
  });

  it("dialog tambah: otomatis mengisi division_id dari user login", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-types" && c.method === "get") return { data: [] };
      if (c.url === "/divisions") return { data: mockUnits };
      if (c.url === "/work-types" && c.method === "post") {
        return { status: 201, data: { ...mockWorkType, id: "wt-new", name: "Penarikan Kabel" } };
      }
    });

    // Render dengan user PM yang memiliki division_id FTTX
    renderRoute("/work-types", {
      me: {
        user_id: "u-pm",
        email: "pm@visiontech.co.id",
        role: "PROJECT_MANAGER",
        permissions: ["create:plan", "read:plan"],
        division_id: "11111111-2222-3333-4444-555555555555",
      },
    });

    await screen.findByText(/Belum ada jenis pekerjaan/);
    fireEvent.click(screen.getAllByRole("button", { name: "Tambah jenis" })[0]);

    const dialog = screen.getByRole("dialog", { name: "Tambah jenis pekerjaan" });
    expect(dialog).toBeInTheDocument();

    // Field divisi harus terisi otomatis dengan division_id user
    const divisionSelect = within(dialog).getByLabelText("Divisi") as HTMLSelectElement;
    await waitFor(() => expect(divisionSelect.value).toBe("11111111-2222-3333-4444-555555555555"));

    // Isi nama jenis pekerjaan
    fireEvent.change(within(dialog).getByLabelText("Nama jenis"), { target: { value: "Penarikan Kabel" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));

    await waitFor(() => expect(calls.some((c) => c.method === "post")).toBe(true));
    const postCall = calls.find((c) => c.method === "post");
    expect(postCall?.data).toMatchObject({
      name: "Penarikan Kabel",
      division_id: "11111111-2222-3333-4444-555555555555",
    });
  });

  it("dialog ubah: mempertahankan division_id jenis pekerjaan dan dapat diperbarui", async () => {
    const calls = mockApi((c) => {
      if (c.url === "/work-types" && c.method === "get") return { data: [mockWorkType] };
      if (c.url === "/divisions") return { data: mockUnits };
      if (c.url === "/work-types/wt-01" && c.method === "put") {
        return { status: 200, data: mockWorkType };
      }
    });

    renderRoute("/work-types", {
      me: {
        user_id: "u-super",
        email: "admin@visiontech.co.id",
        role: "SUPER_ADMIN",
        permissions: ["create:plan", "read:plan"],
        division_id: "11111111-2222-3333-4444-555555555555",
      },
    });

    expect(await screen.findByText("Penyambungan Kabel FO")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ubah" }));

    const dialog = screen.getByRole("dialog", { name: "Ubah jenis pekerjaan" });
    expect(dialog).toBeInTheDocument();

    const divisionSelect = within(dialog).getByLabelText("Divisi") as HTMLSelectElement;
    await waitFor(() => expect(divisionSelect.value).toBe("11111111-2222-3333-4444-555555555555"));

    // Tunggu opsi units muncul
    await within(dialog).findByText(/Mechanical Electrical/);

    // Super Admin dapat mengganti divisi ke MEP
    fireEvent.change(divisionSelect, { target: { value: "22222222-3333-4444-5555-666666666666" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));

    await waitFor(() => expect(calls.some((c) => c.method === "put")).toBe(true));
    const putCall = calls.find((c) => c.method === "put");
    expect(putCall?.data).toMatchObject({
      name: "Penyambungan Kabel FO",
      division_id: "22222222-3333-4444-5555-666666666666",
    });
  });
});
