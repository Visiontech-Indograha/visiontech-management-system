/**
 * Label status Bahasa Indonesia — satu sumber (docs/11 §5). Status rencana kerja & dokumen mengikuti alur rencana kerja v2
 * (keputusan pemilik 2026-10-03, flowchart SK2 di FigJam).
 * Nilai yang tidak dikenal ditampilkan apa adanya.
 */
export const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Draf",
  PUBLISHED: "Terbit",
  ACCEPTED: "Diterima",
  APPEALED: "Revisi diminta",
  IN_PROGRESS: "Berjalan",
  COMPLETION_REVIEW: "Pengajuan penutupan",
  COMPLETED: "Selesai",
  CANCELLED: "Dibatalkan",
  SUBMITTED: "Menunggu persetujuan",
  ONGOING: "Berjalan",
  RESUBMITTED: "Dikirim ulang",
  APPROVED: "Disetujui",
  CHANGES_REQUESTED: "Perlu perbaikan",
  PENDING_PM: "Menunggu PM",
  AWAITING_LEADER_ACCEPTANCE: "Menunggu ketua",
  AWAITING_ACCEPTANCE: "Menunggu tanda tangan",
  EFFECTIVE: "Berlaku",
  REJECTED: "Ditolak",
  SUPERSEDED: "Tidak berlaku",
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
  IN_REVIEW: "Ditinjau",
  RESOLVED: "Selesai",
  WITHDRAWN: "Ditarik PM",
  // Perintah kerja (work_order_status)
  WAITING_SURVEY: "Menunggu survei",
  SURVEY_IN_PROGRESS: "Survei berjalan",
  SURVEY_SUBMITTED: "Survei terkirim",
  READY_TO_EXECUTE: "Siap dikerjakan",
  BAST_SIGNED: "Surat serah terima terbit",
  // Hasil cadangan
  SUCCESS: "Berhasil",
  FAILED: "Gagal",
  PARTIAL_FAILURE: "Gagal sebagian",
  // Cuti
  APPROVED_BY_PM: "Menunggu HR",
  APPROVED_BY_HR: "Disetujui",
  DONE: "Selesai",
  PARTIAL: "Selesai sebagian",
  LATE: "Terlambat",
  OVERDUE: "Terlambat",
  NOT_STARTED: "Belum mulai",
  ROLLOVER_REQUESTED: "Minta pindah hari",
  ROLLED_OVER: "Pindah hari",
  // Aset V2 (asset_status_enum)
  ready: "Siap",
  allocated: "Dialokasikan",
  loaned: "Dipinjam",
  damaged: "Rusak",
  lost: "Hilang",
  pension: "Pensiun",
};

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

const GREEN = ["DONE", "COMPLETED", "APPROVED", "ACCEPTED", "EFFECTIVE", "ACTIVE", "VERIFIED", "CURRENT", "AVAILABLE", "AUTO_VALID", "RESOLVED", "ready"];
const RED = ["LATE", "OVERDUE", "REJECTED", "CANCELLED", "INACTIVE", "damaged", "lost"];
const BLUE = ["IN_PROGRESS", "PUBLISHED", "IN_USE", "allocated", "loaned", "ONGOING"];
const GREY = ["DRAFT", "SUPERSEDED", "WITHDRAWN", "pension"];

/** Warna badge mengikuti prototype/js/ui.js `badge`. */
export function statusTone(status: string): StatusTone {
  if (GREEN.includes(status)) return "success";
  if (RED.includes(status)) return "danger";
  if (BLUE.includes(status)) return "info";
  if (GREY.includes(status)) return "neutral";
  return "warning";
}

export const statusLabel = (status: string) => STATUS_LABEL[status] ?? status;

const SIGNER_ROLE: Record<string, string> = { ISSUER: "Penerbit", ACCEPTOR: "Penerima", WITNESS: "Saksi", APPROVER: "Penyetuju" };

/** Label peran penanda tangan (enum signature_role). */
export const signerRoleLabel = (role: string | null | undefined) => (role ? (SIGNER_ROLE[role] ?? role) : "-");

/** Kategori pekerjaan rencana kerja (daftar tetap, alur rencana kerja v2). */
export const CATEGORY_LABEL: Record<string, string> = {
  INSTALASI: "Instalasi",
  PEMELIHARAAN: "Pemeliharaan",
  PERBAIKAN: "Perbaikan",
  SURVEI: "Survei",
  LAINNYA: "Lainnya",
};
