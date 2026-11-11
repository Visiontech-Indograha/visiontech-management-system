import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { SystemSettingsList } from "@/components/organisms/system/SystemSettingsList";
import { settingErrorMessage, settingSourceLabel } from "@/lib/systemSettings";
import { ApiError } from "@/lib/apiClient";
import { apiError, mockApi } from "@/test/utils";

const row = (over: Record<string, unknown> = {}) => ({
  key: "ROLE_ASSIGNMENT_ENABLED", label: "Peran ganda", description: "Mengizinkan satu orang memegang dua peran.",
  type: "bool", value: false, source: "env_default", env_default: false, locked: false, updated_at: null, ...over,
});

function renderList() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SystemSettingsList />
    </QueryClientProvider>,
  );
}

describe("Setelan sistem", () => {
  it("memetakan asal nilai ke bahasa awam", () => {
    expect(settingSourceLabel("db")).toBe("Diubah di sini");
    expect(settingSourceLabel("env_default")).toBe("Dari server");
    expect(settingSourceLabel("env_force")).toBe("Dari server");
  });

  it("pesan SETTING_LOCKED awam, tanpa kode", () => {
    const msg = settingErrorMessage(new ApiError("SETTING_LOCKED", "x", 409));
    expect(msg).toMatch(/dikunci/);
    expect(msg).not.toMatch(/SETTING_LOCKED/);
  });

  it("sakelar nonaktif bila dikunci", async () => {
    mockApi((c) => (c.method === "get" ? { data: [row({ locked: true, source: "env_force" })] } : undefined));
    renderList();
    const btn = await screen.findByRole("switch", { name: /Peran ganda/ });
    expect((btn as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/dikunci server/)).toBeTruthy();
  });

  it("meminta konfirmasi sebelum mengubah, lalu mengirim nilai baru", async () => {
    const calls = mockApi((c) => {
      if (c.method === "get") return { data: [row()] };
      if (c.method === "put") return { data: [row({ value: true, source: "db" })] };
      return undefined;
    });
    renderList();
    fireEvent.click(await screen.findByRole("switch", { name: /Peran ganda/ }));
    expect(calls.some((x) => x.method === "put")).toBe(false);
    fireEvent.click(await screen.findByRole("button", { name: "Ya, nyalakan" }));
    await waitFor(() => expect(calls.find((x) => x.method === "put")?.data).toEqual({ values: { ROLE_ASSIGNMENT_ENABLED: true } }));
    expect(await screen.findByText("Diubah di sini")).toBeTruthy();
  });

  it("409 SETTING_LOCKED tampil sebagai pesan awam di dialog", async () => {
    mockApi((c) => {
      if (c.method === "get") return { data: [row()] };
      return apiError(409, "SETTING_LOCKED", "Setelan dikunci oleh pengaturan pemasangan.");
    });
    renderList();
    fireEvent.click(await screen.findByRole("switch", { name: /Peran ganda/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Ya, nyalakan" }));
    expect(await screen.findByText(/dikunci oleh pengaturan server/)).toBeTruthy();
  });
});
