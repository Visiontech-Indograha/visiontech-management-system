import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/lib/apiTypes";
import type { Permission } from "@/lib/permissions";

export type ArchiveItem = components["schemas"]["ArchiveItemOut"];

export const ARCHIVE_KEY = ["archive"] as const;

/** Modul Arsip. `slug` dan `permission` sama dengan api/app/modules/archive/schemas/archive_modules.py. */
export const ARCHIVE_MODULES: readonly { slug: string; label: string; codeLabel: string; permission: Permission }[] = [
  { slug: "tools", label: "Peralatan", codeLabel: "Kode", permission: "manage:assets" },
  { slug: "vehicles", label: "Kendaraan", codeLabel: "Plat nomor", permission: "manage:assets" },
  { slug: "clients", label: "Klien", codeLabel: "Kode", permission: "create:plan" },
  { slug: "divisions", label: "Divisi", codeLabel: "Kode", permission: "manage:divisions" },
  { slug: "job-positions", label: "Jabatan", codeLabel: "Kode", permission: "manage:users" },
  { slug: "mess", label: "Mess", codeLabel: "Kode", permission: "manage:mess" },
];

export const archiveUrl = (slug: string) => `/archive/${slug}`;

/** Pulihkan satu item. Galat 409 (konflik atau induk masih diarsipkan) membawa pesan awam dari API. */
export function useRestoreArchived(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.post<ArchiveItem>(`${archiveUrl(slug)}/${id}/restore`)).data,
    // Data pulih muncul lagi di daftar modulnya, jadi semua daftar disegarkan.
    onSuccess: () => qc.invalidateQueries(),
  });
}
