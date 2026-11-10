import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

type S = components["schemas"];
export type SetupStatus = S["SetupStatusOut"];
export type SetupAdminInput = S["SetupAdminIn"];

/** GET /setup/status (publik): apakah instalasi masih perlu penyiapan dan apakah server mengaktifkannya. */
export const useSetupStatus = () =>
  useQuery({
    queryKey: ["setup", "status"],
    queryFn: async () => (await api.get<SetupStatus>("/setup/status")).data,
    staleTime: 60_000,
    retry: false,
  });

/** POST /setup/admin (publik): buat Super Admin pertama. 403 kode salah; 409 sudah disiapkan / email dipakai. */
export async function createFirstAdmin(input: SetupAdminInput): Promise<S["SetupAdminOut"]> {
  return (await api.post<S["SetupAdminOut"]>("/setup/admin", input)).data;
}
