/**
 * Label status Bahasa Indonesia — satu sumber (docs/11 §5), disalin dari prototype/js/ui.js `states`.
 * Nilai yang tidak dikenal ditampilkan apa adanya.
 */
export const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Draft",
  PUBLISHED: "SK terbit",
  ACCEPTED: "Diterima",
  APPEALED: "Banding",
  IN_PROGRESS: "Berjalan",
  COMPLETION_REVIEW: "Review penyelesaian",
  COMPLETED: "Selesai",
  CANCELLED: "Dibatalkan",
  SUBMITTED: "Menunggu review",
  APPROVED: "Disetujui",
  CHANGES_REQUESTED: "Perlu perbaikan",
  PENDING_PM: "Menunggu PM",
  AWAITING_LEADER_ACCEPTANCE: "Menunggu ketua",
  AWAITING_ACCEPTANCE: "Menunggu penerimaan",
  EFFECTIVE: "Efektif",
  REJECTED: "Ditolak",
  SUPERSEDED: "Versi sebelumnya",
  ACTIVE: "Aktif",
  INACTIVE: "Nonaktif",
  VERIFIED: "Terverifikasi",
  PENDING: "Menunggu verifikasi",
  CURRENT: "Berlaku",
  NEEDS_REVIEW: "Perlu review",
  AUTO_VALID: "Valid otomatis",
  IN_USE: "Dipakai",
  RESERVED: "Direservasi",
  AVAILABLE: "Tersedia",
  RETURN_PENDING: "Menunggu pemeriksaan",
  OPEN: "Terbuka",
  RESOLVED: "Selesai",
  WITHDRAWN: "Ditarik PM",
};

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

const GREEN = ["COMPLETED", "APPROVED", "ACCEPTED", "EFFECTIVE", "ACTIVE", "VERIFIED", "CURRENT", "AVAILABLE", "AUTO_VALID", "RESOLVED"];
const RED = ["REJECTED", "CANCELLED", "INACTIVE"];
const BLUE = ["IN_PROGRESS", "PUBLISHED", "IN_USE"];
const GREY = ["DRAFT", "SUPERSEDED", "WITHDRAWN"];

/** Warna badge mengikuti prototype/js/ui.js `badge`. */
export function statusTone(status: string): StatusTone {
  if (GREEN.includes(status)) return "success";
  if (RED.includes(status)) return "danger";
  if (BLUE.includes(status)) return "info";
  if (GREY.includes(status)) return "neutral";
  return "warning";
}

export const statusLabel = (status: string) => STATUS_LABEL[status] ?? status;
