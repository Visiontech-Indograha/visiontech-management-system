import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { components } from "@/lib/api-types";
import type { UserCreate, UserCreated, UserOut, UserPage, UserUpdate } from "@/lib/types";

export interface UserFilters {
  q?: string;
  role?: string;
  is_active?: string; // "true" | "false" | ""
  page: number;
}

const KEY = ["users"] as const;

export function useUsers(filters: UserFilters) {
  return useQuery({
    queryKey: [...KEY, filters],
    queryFn: async () => {
      const params = {
        page: filters.page,
        page_size: 25,
        sort: "full_name",
        ...(filters.q ? { q: filters.q } : {}),
        ...(filters.role ? { role: filters.role } : {}),
        ...(filters.is_active ? { is_active: filters.is_active } : {}),
      };
      return (await api.get<UserPage>("/users", { params })).data;
    },
    placeholderData: keepPreviousData,
  });
}

function useInvalidating<TVars, TData>(fn: (v: TVars) => Promise<TData>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export const useCreateUser = () =>
  useInvalidating(async (data: UserCreate) => (await api.post<UserCreated>("/users", data)).data);

export const useUpdateUser = () =>
  useInvalidating(
    async ({ id, data }: { id: string; data: UserUpdate }) =>
      (await api.patch<UserOut>(`/users/${id}`, data)).data,
  );

export const useResetPassword = () =>
  useInvalidating(
    async (id: string) =>
      (await api.post<components["schemas"]["PasswordResetOut"]>(`/users/${id}/reset-password`)).data,
  );

export const useDeactivateUser = () =>
  useInvalidating(
    async ({ id, reason, resign_date }: { id: string; reason: string; resign_date?: string }) =>
      (await api.post<UserOut>(`/users/${id}/deactivate`, { reason, resign_date: resign_date || null })).data,
  );

export const useActivateUser = () =>
  useInvalidating(async (id: string) => (await api.post<UserOut>(`/users/${id}/activate`)).data);

export function useOpenItems(id: string | null) {
  return useQuery({
    queryKey: ["users", id, "open-items"],
    enabled: !!id,
    queryFn: async () =>
      (await api.get<components["schemas"]["OpenItemsOut"]>(`/users/${id}/open-items`)).data,
  });
}
