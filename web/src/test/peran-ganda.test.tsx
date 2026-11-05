import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMe } from "@/app/mockSession";
import { roleAddBlocker, roleScopeLines } from "@/lib/roleAssignments";
import { apiError, mockApi, renderRoute } from "./utils";

const EID = "00000000-0000-4000-8000-0000000000e1";
const UID = "11111111-1111-4111-8111-111111111111";
const employee = {
  employee_id: EID, employee_no: "VT-001", full_name: "Test User", office_id: "o1", office_name: "Kantor Pusat",
  division_id: "u1", division_name: "CCTV & ACS", position_id: "p1", position_code: "TEK", position_name: "Teknisi",
  join_date: "2024-01-01", pkwt_end_date: null, photo_file_id: null, face_enrolled: false,
  offboarding_status: "active", archived: false, email: null, addresses: [],
};
const sa = { ...mockMe("HR"), permissions: [...mockMe("HR")!.permissions, "manage:role_assignments"] } as never;
const hr = mockMe("HR") as never;
const rowHr = {
  assignment_id: "a1", user_id: UID, role: "ADMIN_HR_GA", office_id: "o1", office_name: "Kantor Pusat",
  source: "ASSIGNED", created_at: "2026-11-01T00:00:00Z",
};

function api(opts: { list?: unknown[]; primary?: string; post?: ReturnType<typeof apiError> | { status: number; data: unknown } } = {}) {
  return mockApi((c) => {
    if (c.url === `/employees/${EID}`) return { data: employee };
    if (c.url === `/employees/${EID}/documents`) return { data: { items: [], total: 0 } };
    if (c.url === `/employees/${EID}/account`)
      return { data: { exists: true, user_id: UID, system_role: opts.primary ?? "EMPLOYEE", failed_logins: 0, is_active: true } };
    if (c.url === "/offices") return { data: [{ id: "o1", name: "Kantor Pusat" }, { id: "o2", name: "Kantor Timur" }] };
    if (c.url === `/users/${UID}/role-assignments` && c.method === "post") return opts.post ?? { status: 201, data: rowHr };
    if (c.url === `/users/${UID}/role-assignments`) return { data: opts.list ?? [] };
    if (c.url === `/users/${UID}/role-assignments/a1` && c.method === "delete") return { status: 204, data: null };
    return undefined;
  });
}

describe("Peran tambahan dan kantor", () => {
  it("tidak tampil bagi yang tanpa izin", async () => {
    api();
    renderRoute(`/directory/${EID}`, { me: hr });
    await screen.findByText("Test User");
    expect(screen.queryByText("Peran tambahan dan kantor")).not.toBeInTheDocument();
  });

  it("tampil bagi yang berizin: kosong, lalu daftar", async () => {
    api();
    renderRoute(`/directory/${EID}`, { me: sa });
    expect(await screen.findByText("Belum ada peran tambahan.")).toBeInTheDocument();
  });

  it("daftar menampilkan peran dan kantor", async () => {
    api({ list: [rowHr, { ...rowHr, assignment_id: "a2", role: "OPERATIONAL_MANAGER", office_id: null, office_name: null }] });
    renderRoute(`/directory/${EID}`, { me: sa });
    expect(await screen.findByText(/HR · Kantor Pusat/)).toBeInTheDocument();
    expect(screen.getByText(/Operational Manager · Semua kantor/)).toBeInTheDocument();
  });

  it("galat memuat daftar", async () => {
    mockApi((c) => {
      if (c.url === `/employees/${EID}`) return { data: employee };
      if (c.url === `/employees/${EID}/account`) return { data: { exists: true, user_id: UID, failed_logins: 0 } };
      if (c.url === `/users/${UID}/role-assignments`) return { status: 500, data: {} };
      return undefined;
    });
    renderRoute(`/directory/${EID}`, { me: sa });
    expect(await screen.findByText("Daftar peran tidak dapat dimuat.")).toBeInTheDocument();
  });

  it("menambah peran HR dengan kantor dan Idempotency-Key", async () => {
    const calls = api();
    renderRoute(`/directory/${EID}`, { me: sa });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah peran" }));
    fireEvent.change(await screen.findByLabelText("Peran tambahan"), { target: { value: "ADMIN_HR_GA" } });
    fireEvent.change(await screen.findByLabelText("Kantor"), { target: { value: "o1" } });
    fireEvent.click(screen.getByRole("button", { name: "Simpan peran" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post")).toBe(true));
    const post = calls.find((c) => c.method === "post")!;
    expect(post.data).toMatchObject({ role: "ADMIN_HR_GA", office_id: "o1" });
    expect(JSON.stringify(post.headers)).toContain("Idempotency-Key");
  });

  it("OM otomatis semua kantor (tanpa pilihan kantor)", async () => {
    const calls = api();
    renderRoute(`/directory/${EID}`, { me: sa });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah peran" }));
    fireEvent.change(await screen.findByLabelText("Peran tambahan"), { target: { value: "OPERATIONAL_MANAGER" } });
    expect(screen.queryByLabelText("Kantor")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Simpan peran" }));
    await waitFor(() => expect(calls.some((c) => c.method === "post")).toBe(true));
    expect(calls.find((c) => c.method === "post")!.data).toMatchObject({ role: "OPERATIONAL_MANAGER", office_id: null });
  });

  it("HR dan Finance bersamaan ditolak di layar tanpa kirim", async () => {
    const calls = api({ list: [rowHr] });
    renderRoute(`/directory/${EID}`, { me: sa });
    await screen.findByText(/HR · Kantor Pusat/);
    fireEvent.click(screen.getByRole("button", { name: "Tambah peran" }));
    fireEvent.change(await screen.findByLabelText("Peran tambahan"), { target: { value: "FINANCE" } });
    expect(await screen.findByText("HR dan Finance tidak boleh dipegang bersamaan oleh satu orang.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Menyimpan..." })).toBeDisabled();
    expect(calls.some((c) => c.method === "post")).toBe(false);
  });

  it("422 dipetakan ke kolom", async () => {
    api({ post: apiError(422, "VALIDATION_ERROR", "Tidak valid", { fields: { office_id: ["x"] } }) });
    renderRoute(`/directory/${EID}`, { me: sa });
    fireEvent.click(await screen.findByRole("button", { name: "Tambah peran" }));
    fireEvent.change(await screen.findByLabelText("Peran tambahan"), { target: { value: "FINANCE" } });
    fireEvent.change(await screen.findByLabelText("Kantor"), { target: { value: "o2" } });
    fireEvent.click(screen.getByRole("button", { name: "Simpan peran" }));
    expect(await screen.findByText("Isian tidak valid. Periksa panjang atau format.")).toBeInTheDocument();
    expect(screen.getByText("Periksa kolom yang ditandai.")).toBeInTheDocument();
  });

  it("mencabut peran setelah konfirmasi", async () => {
    const calls = api({ list: [rowHr] });
    renderRoute(`/directory/${EID}`, { me: sa });
    fireEvent.click(await screen.findByRole("button", { name: "Cabut HR" }));
    fireEvent.click(await screen.findByRole("button", { name: "Cabut" }));
    await waitFor(() => expect(calls.some((c) => c.method === "delete")).toBe(true));
  });
});

describe("aturan peran dan tampilan peran efektif", () => {
  const base = { role: "FINANCE", primaryRole: "EMPLOYEE", held: ["EMPLOYEE"], extraCount: 0, isSelf: false };
  it("aturan terlarang", () => {
    expect(roleAddBlocker(base)).toBeNull();
    expect(roleAddBlocker({ ...base, isSelf: true })).toMatch(/akun sendiri/);
    expect(roleAddBlocker({ ...base, primaryRole: "SUPER_ADMIN" })).toMatch(/Super Admin/);
    expect(roleAddBlocker({ ...base, extraCount: 2 })).toMatch(/Paling banyak 2/);
  });
  it("HR dua kantor: kantor beda boleh, kantor sama ditolak, OM dobel ditolak, HR+Finance tetap ditolak", () => {
    const hr = { role: "ADMIN_HR_GA", primaryRole: "EMPLOYEE", held: ["EMPLOYEE", "ADMIN_HR_GA"], extraCount: 1, isSelf: false };
    const scopes = [{ role: "ADMIN_HR_GA", office_id: "A" }];
    expect(roleAddBlocker({ ...hr, scopes, officeId: "B" })).toBeNull();
    expect(roleAddBlocker({ ...hr, scopes, officeId: "A" })).toMatch(/kantor yang sama/);
    const om = { ...hr, role: "OPERATIONAL_MANAGER", held: ["EMPLOYEE", "OPERATIONAL_MANAGER"] };
    expect(roleAddBlocker({ ...om, scopes: [{ role: "OPERATIONAL_MANAGER", office_id: null }] })).toMatch(/kantor yang sama/);
    expect(roleAddBlocker({ ...hr, role: "FINANCE", scopes, officeId: "B" })).toMatch(/HR dan Finance/);
  });
  it("tanpa role_scopes tampilan lama tak berubah", () => {
    expect(roleScopeLines({})).toEqual([]);
    expect(roleScopeLines({ role_scopes: [] })).toEqual([]);
  });
  it("teks berlaku untuk kantor", () => {
    expect(roleScopeLines({ role_scopes: [{ role: "ADMIN_HR_GA", office_name: "Kantor Timur", primary: false }] })).toEqual([
      "HR · berlaku untuk kantor Kantor Timur",
    ]);
  });
  it("menu menampilkan teks kantor dari role_scopes", async () => {
    mockApi(() => undefined);
    const me = { ...mockMe("HR"), role_scopes: [{ role: "ADMIN_HR_GA", office_name: "Kantor Timur", primary: false }] } as never;
    renderRoute("/account", { me });
    expect((await screen.findAllByText("HR · berlaku untuk kantor Kantor Timur")).length).toBeGreaterThan(0);
  });
});
