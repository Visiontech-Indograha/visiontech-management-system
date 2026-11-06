import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { RoleAssignmentAddDialog } from "./RoleAssignmentAddDialog";
import { ACTION_LABEL } from "@/lib/auditLabels";

function setup(isSelf: boolean) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <RoleAssignmentAddDialog userId="u1" primaryRole="EMPLOYEE" held={[]} scopes={[]} extraCount={0} isSelf={isSelf} onClose={vi.fn()} />
    </QueryClientProvider>,
  );
}

describe("RoleAssignmentAddDialog", () => {
  it("diblokir: Simpan nonaktif bertulisan normal, Batal tetap aktif", async () => {
    setup(true);
    await userEvent.selectOptions(screen.getByLabelText("Peran tambahan"), "OPERATIONAL_MANAGER");
    expect(screen.getByText("Anda tidak dapat mengubah peran akun sendiri.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Simpan peran" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByText("Menyimpan...")).toBeNull();
    expect((screen.getByRole("button", { name: "Batal" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("tidak diblokir: Simpan aktif", () => {
    setup(false);
    expect((screen.getByRole("button", { name: "Simpan peran" }) as HTMLButtonElement).disabled).toBe(false);
  });
});

describe("label audit", () => {
  it("peran tambahan berlabel awam, label lama utuh", () => {
    expect(ACTION_LABEL.ROLE_ASSIGNMENT_ADD).toBe("Peran tambahan diberikan");
    expect(ACTION_LABEL.ROLE_ASSIGNMENT_REVOKE).toBe("Peran tambahan dicabut");
    expect(ACTION_LABEL.DEVICE_KEY_REGISTERED).toBe("Perangkat didaftarkan");
  });
});
