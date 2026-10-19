/**
 * web/src/components/organisms/audit/BackupRegistryTable.tsx
 * Tabel riwayat pencatatan backup basis data PostgreSQL (Master Schema V2).
 * Menampilkan siklus backup, periode data, ukuran terkompresi, SHA-256, dan aksi unduh berkas.
 */

import React, { useState } from "react";
import { formatDateTime } from "@/lib/format";
import { toDownloadUrl } from "@/lib/mediaUtils";
import { useBackupRegistry, type BackupRegistryItem } from "@/services/backupRegistryService";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { ActionButton } from "@/components/molecules/ActionButton";
import { Button } from "@/components/atoms/Button";
import {
  TableBlock,
  TableBlockBody,
  TableBlockCell,
  TableBlockHead,
  TableBlockHeaderCell,
  TableBlockRow,
} from "@/components/molecules/TableBlock";
import {
  CheckCircle2,
  Copy,
  Download,
  HardDriveDownload,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";

export const BackupRegistryTable: React.FC = () => {
  const backups = useBackupRegistry(50);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyChecksum = (checksum: string, id: string) => {
    navigator.clipboard.writeText(checksum);
    setCopiedId(id);
    toast.success("SHA-256 Checksum disalin ke papan klip");
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getCycleBadge = (cycle: string) => {
    switch (cycle.toUpperCase()) {
      case "DAILY":
        return "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300";
      case "WEEKLY":
        return "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300";
      case "MONTHLY":
        return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300";
      default:
        return "bg-slate-50 text-slate-700 border-slate-200 dark:bg-slate-900/40 dark:text-slate-300";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-ink flex items-center gap-2">
            <HardDriveDownload className="w-5 h-5 text-indigo-600" />
            Registry Cadangan Basis Data (PostgreSQL Backups)
          </h3>
          <p className="text-xs text-mist">
            Daftar snapshot arsip basis data otomatis dan terjadwal sesuai kepatuhan retensi data ISO 27001.
          </p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-panel border border-line bg-surface shadow-card">
        <TableBlock className="w-full text-left text-sm">
          <TableBlockHead className="border-b border-line text-mist">
            <TableBlockRow>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Waktu Eksekusi</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Siklus & Periode</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Ukuran</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Integritas (SHA-256)</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Status</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 text-right font-medium">Aksi</TableBlockHeaderCell>
            </TableBlockRow>
          </TableBlockHead>
          <TableBlockBody>
            {backups.isPending && (
              <TableBlockRow aria-hidden>
                <TableBlockCell colSpan={6} className="px-4 py-4">
                  <LoadingBar className="h-5 w-3/4" />
                </TableBlockCell>
              </TableBlockRow>
            )}

            {backups.isError && (
              <TableBlockRow>
                <TableBlockCell colSpan={6} className="px-4 py-6 text-center text-danger">
                  Gagal memuat registry backup basis data.{" "}
                  <ActionButton variant="outline" size="sm" onClick={() => backups.refetch()}>
                    Coba lagi
                  </ActionButton>
                </TableBlockCell>
              </TableBlockRow>
            )}

            {backups.data && backups.data.length === 0 && (
              <TableBlockRow>
                <TableBlockCell colSpan={6} className="px-4 py-8 text-center text-mist">
                  Belum ada catatan snapshot cadangan basis data dalam sistem.
                </TableBlockCell>
              </TableBlockRow>
            )}

            {backups.data?.map((item: BackupRegistryItem) => {
              const downloadUrl = toDownloadUrl(item.file_path_url);
              const isSuccess = item.status === "SUCCESS";

              return (
                <TableBlockRow key={item.backup_id} className="h-12 border-b border-line hover:bg-surface-muted/50">
                  <TableBlockCell className="whitespace-nowrap px-4 py-2 text-ink">
                    {formatDateTime(item.created_at)}
                  </TableBlockCell>

                  <TableBlockCell className="px-4 py-2">
                    <span
                      className={`inline-block px-2 py-0.5 text-[11px] font-semibold rounded border mr-2 ${getCycleBadge(
                        item.backup_cycle
                      )}`}
                    >
                      {item.backup_cycle}
                    </span>
                    <span className="text-xs text-mist">
                      {item.period_start} s.d. {item.period_end}
                    </span>
                  </TableBlockCell>

                  <TableBlockCell className="px-4 py-2 font-medium text-ink">
                    {Number(item.compressed_size_mb).toFixed(2)} MB
                  </TableBlockCell>

                  <TableBlockCell className="px-4 py-2">
                    <div className="flex items-center gap-1.5 font-mono text-xs text-mist">
                      <span>{item.sha256_checksum.slice(0, 12)}...{item.sha256_checksum.slice(-6)}</span>
                      <button
                        type="button"
                        onClick={() => handleCopyChecksum(item.sha256_checksum, item.backup_id)}
                        className="p-1 rounded hover:bg-surface-muted text-mist hover:text-ink transition-colors"
                        title="Salin Full SHA-256 Checksum"
                      >
                        {copiedId === item.backup_id ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </TableBlockCell>

                  <TableBlockCell className="px-4 py-2">
                    {isSuccess ? (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Berhasil
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-danger">
                        <ShieldAlert className="w-3.5 h-3.5" />
                        {item.status}
                      </span>
                    )}
                  </TableBlockCell>

                  <TableBlockCell className="px-4 py-2 text-right">
                    <Button asChild size="sm" variant="outline" className="h-8 px-2.5 text-xs">
                      <a href={downloadUrl} download>
                        <Download className="w-3.5 h-3.5 mr-1 text-indigo-600" />
                        Unduh
                      </a>
                    </Button>
                  </TableBlockCell>
                </TableBlockRow>
              );
            })}
          </TableBlockBody>
        </TableBlock>
      </div>
    </div>
  );
};
