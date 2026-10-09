/** Tabel yang diaudit trigger tg_audit_row (db/02_functions.sql, 04_signature_auth.sql, 05_face.sql). */
export const AUDIT_ENTITIES: Record<string, string> = {
  work_plan: "Rencana Kerja / pekerjaan",
  plan_document: "Dokumen rencana kerja",
  plan_change: "Perubahan rencana kerja",
  employee_document: "Berkas karyawan",
  asset_allocation: "Alokasi aset",
  incident_report: "Laporan insiden",
  overtime_log: "Lembur",
  qr_token: "Token QR",
  document_signature: "Tanda tangan dokumen",
  face_enrollment: "Pendaftaran wajah",
};

export const ACTION_LABEL: Record<string, string> = { INSERT: "Tambah", UPDATE: "Ubah", DELETE: "Hapus" };
