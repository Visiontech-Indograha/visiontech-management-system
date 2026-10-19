/**
 * web/src/services/backupRegistryService.ts
 * Layanan komunikasi API untuk Registry Backup Basis Data PostgreSQL.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";

export interface BackupRegistryItem {
  backup_id: string;
  backup_cycle: "DAILY" | "WEEKLY" | "MONTHLY" | string;
  period_start: string;
  period_end: string;
  file_path_url: string;
  compressed_size_mb: number;
  sha256_checksum: string;
  status: "SUCCESS" | "FAILED" | "PENDING" | string;
  created_at: string;
}

export interface BackupRegistryCreate {
  backup_cycle: string;
  period_start: string;
  period_end: string;
  file_path_url: string;
  compressed_size_mb: number;
  sha256_checksum: string;
  status?: string;
}

const KEY = ["backup-registry"] as const;

export function useBackupRegistry(limit = 50) {
  return useQuery({
    queryKey: [...KEY, limit],
    queryFn: async () => {
      const resp = await api.get<BackupRegistryItem[]>("/backup-registry", {
        params: { limit },
      });
      return resp.data;
    },
  });
}

export function useRecordBackup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: BackupRegistryCreate) => {
      const resp = await api.post<BackupRegistryItem>("/backup-registry", payload);
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
    },
  });
}
