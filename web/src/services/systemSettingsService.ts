import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";

export type SystemSetting = components["schemas"]["SystemSettingOut"];

const KEY = ["system-settings"] as const;

/** GET /system/settings (izin manage:system_settings, hanya SUPER_ADMIN). */
export const useSystemSettings = () =>
  useQuery({ queryKey: KEY, queryFn: async () => (await api.get<SystemSetting[]>("/system/settings")).data });

/** PUT /system/settings: ubah satu sakelar; 409 SETTING_LOCKED bila dikunci pemasangan. */
export function useUpdateSystemSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (a: { key: string; value: boolean }) =>
      (await api.put<SystemSetting[]>("/system/settings", { values: { [a.key]: a.value } })).data,
    onSuccess: (data) => qc.setQueryData(KEY, data),
  });
}
