// Tes arsitektur G0 (docs/rencana/struktur-dan-kualitas-kode.md 1.1, 1.4, 1.5, 1.7). Hanya membaca berkas sumber.
// Daftar BASELINE_* hanya boleh MENYUSUT: hapus entri saat berkasnya diganti nama, dipindah, atau dihapus.
import { describe, expect, it } from "vitest";

// Semua berkas di src/ sebagai teks mentah (tanpa API Node, agar lolos tsc aplikasi).
const RAW = import.meta.glob<string>("/src/**/*.{ts,tsx}", { query: "?raw", import: "default", eager: true });
const SUMBER_TEKS: Record<string, string> = {};
for (const [k, v] of Object.entries(RAW)) SUMBER_TEKS[k.slice("/src/".length)] = v;
const FILES = Object.keys(SUMBER_TEKS);
const isTest = (f: string) => /\.test\.tsx?$/.test(f);
const read = (f: string) => SUMBER_TEKS[f];
const sumber = () => FILES.filter((f) => /\.tsx?$/.test(f) && !isTest(f) && !f.startsWith("test/"));

/** Berkas *Modal*.tsx lama. Nama baru memakai *Dialog (G2 butir 9 mengganti nama bertahap). */
const BASELINE_MODAL_NAMES = [
  "components/molecules/Modal.tsx",
  "components/organisms/clients/ClientSitesModal.tsx",
  "components/organisms/media/ImageLightboxModal.tsx",
  "components/organisms/media/PdfViewerModal.tsx",
  "components/organisms/media/UniversalMediaModal.tsx",
  "components/organisms/work-completions/WorkCompletionDetailModal.tsx",
  "components/organisms/work-orders/WorkOrderAssignModal.tsx",
  "components/organisms/work-orders/WorkOrderBastModal.tsx",
  "components/organisms/work-orders/WorkOrderCreateModal.tsx",
  "components/organisms/work-orders/WorkOrderSurveyReviewModal.tsx",
];

/** Tes lama di src/test/ (belum dipindah ke samping berkas, Fase 4). Tes BARU di sini hanya bila lintas domain. */
// Satu nama per baris (bukan larik string) agar pemindai rahasia tidak salah mengira "key*" sebagai kunci API.
const BASELINE_TESTS_DI_SRC_TEST = `
  account.test.tsx
  alokasi-mingguan.test.tsx
  android-download.test.tsx
  api.test.ts
  aset-pinjam-jadwal.test.tsx
  aset-tim-jadwal.test.tsx
  assets.test.tsx
  attendance-office.test.tsx
  attendance.test.tsx
  audit.test.tsx
  auth.test.tsx
  b17-kecil.test.tsx
  b3-project-delete.test.tsx
  b3-ux-remaining.test.tsx
  b3-work-completion.test.tsx
  b3-work-plans.test.tsx
  caddy-headers.test.ts
  cetak.test.tsx
  corrections-panel.test.tsx
  corrections.test.ts
  daily-plans.test.tsx
  dialog-dirty-b3.test.tsx
  directory.test.tsx
  divisi-jabatan.test.tsx
  exports.test.tsx
  face-camera.test.tsx
  field-errors.test.ts
  form-tanpa-validasi-bawaan.test.ts
  format-distance.test.ts
  home.test.tsx
  hseCarousel.test.tsx
  idempotency.test.ts
  inputRules.test.ts
  jenis-pekerjaan-pratinjau.test.ts
  kendali-admin.test.tsx
  keyset-list.test.tsx
  keyset.test.tsx
  leaves-conflict-cancel.test.tsx
  leaves-review.test.tsx
  list-controls.test.tsx
  mess-hunian-kapasitas.test.tsx
  mess-requests.test.tsx
  monitoring.test.tsx
  navigation.test.tsx
  overtime-apply.test.tsx
  overtime-review.test.tsx
  overtime-role-button.test.tsx
  overtime.test.tsx
  page-title.test.tsx
  peran-ganda.test.tsx
  peran-status-matrix.test.ts
  petunjuk-cari-awalan.test.tsx
  photoRefs.test.ts
  qa-web-perbaikan.test.tsx
  refreshLintasTab.test.ts
  regressions.test.tsx
  service-paths.test.ts
  setup-peran-sandi.test.tsx
  sisa-target-klien.test.tsx
  sites.test.tsx
  temuan-e2e-web.test.tsx
  temuan-uji-jadwal.test.tsx
  temuan-uji-pekerjaan-klien.test.tsx
  temuan-uji-web.test.tsx
  ukuran-sentuh-teks.test.ts
  vms-dialog-dirty.test.tsx
  week-surveys-panel.test.tsx
  work-types-copy.test.tsx
  work-types.test.tsx
  zoomCaption.test.tsx
`
  .split("\n")
  .map((n) => n.trim())
  .filter(Boolean);
/** Tes lintas domain / halaman penuh yang sah ditambah di src/test/. */
const LINTAS_DOMAIN = ["arsitektur.test.ts"];

/** Jumlah impor molecules/Modal dan atoms/Dialog pada kode non-tes. Hanya boleh turun (G2 butir 1 menuju 0). */
const MAKS_IMPOR_DIALOG_LAMA = 6;
const IMPOR_DIALOG_LAMA = /from\s+["'][^"']*(molecules\/Modal|atoms\/Dialog|\.\/Modal|\.\/Dialog)["']/g;

/** Berkas > 500 baris (tanpa baris kosong/komentar): batas atas per berkas, hanya boleh turun. */
const BATAS_BERKAS_BESAR: Record<string, number> = {
  "components/organisms/attendance/OfficeCheckInCard.tsx": 509,
  "components/organisms/hse/HseCampaignsPanel.tsx": 611,
  "components/organisms/work-orders/WorkOrderSurveyReviewModal.tsx": 611,
};
const hitungBaris = (f: string) =>
  read(f).split("\n").filter((l: string) => {
    const t = l.trim();
    return t && !t.startsWith("//") && !t.startsWith("*") && !t.startsWith("/*");
  }).length;

describe("arsitektur web", () => {
  it("berkas *Modal*.tsx baru ditolak (pakai *Dialog); baseline tidak memuat berkas yang sudah hilang", () => {
    const modal = FILES.filter((f) => /Modal[^/]*\.tsx$/.test(f) && !isTest(f)).sort();
    expect(modal.filter((f) => !BASELINE_MODAL_NAMES.includes(f)), "Beri nama *Dialog, bukan *Modal").toEqual([]);
    expect(BASELINE_MODAL_NAMES.filter((f) => !FILES.includes(f)), "Hapus dari BASELINE_MODAL_NAMES").toEqual([]);
  });

  it("berkas skema di schemas/ bernama *Schema.ts atau *Schemas.ts", () => {
    expect(FILES.filter((f) => f.startsWith("schemas/") && !isTest(f) && !/Schemas?\.ts$/.test(f))).toEqual([]);
  });

  it("jumlah impor Modal / atoms/Dialog tidak naik", () => {
    let total = 0;
    for (const f of sumber()) total += (read(f).match(IMPOR_DIALOG_LAMA) ?? []).length;
    expect(total).toBeLessThanOrEqual(MAKS_IMPOR_DIALOG_LAMA);
  });

  it("berkas tes baru di src/test/ ditolak kecuali daftar lintas domain", () => {
    const tes = FILES.filter((f) => f.startsWith("test/") && isTest(f)).map((f) => f.slice(5));
    const baru = tes.filter((f) => !BASELINE_TESTS_DI_SRC_TEST.includes(f) && !LINTAS_DOMAIN.includes(f));
    expect(baru, "Letakkan tes di samping berkas sumbernya, atau daftarkan di LINTAS_DOMAIN bila lintas domain").toEqual([]);
    expect(BASELINE_TESTS_DI_SRC_TEST.filter((f) => !tes.includes(f)), "Hapus dari BASELINE_TESTS_DI_SRC_TEST").toEqual([]);
  });

  it("tidak ada barrel index.ts / index.tsx", () => {
    expect(FILES.filter((f) => /(^|\/)index\.tsx?$/.test(f))).toEqual([]);
  });

  it("berkas lebih dari 500 baris tidak bertambah besar dan tidak ada yang baru", () => {
    for (const f of sumber().filter((x) => !x.endsWith("apiTypes.ts"))) {
      const n = hitungBaris(f);
      if (n > 500) expect(n, f).toBeLessThanOrEqual(BATAS_BERKAS_BESAR[f] ?? 500);
    }
  });

  it("pola pelanggar dikenali (kasus uji penegak)", () => {
    expect('import { Modal } from "@/components/molecules/Modal";'.match(IMPOR_DIALOG_LAMA)).toHaveLength(1);
    expect('import { Dialog } from "../atoms/Dialog";'.match(IMPOR_DIALOG_LAMA)).toHaveLength(1);
    expect('import { VmsDialog } from "@/components/molecules/VmsDialog";'.match(IMPOR_DIALOG_LAMA)).toBeNull();
    expect(/Modal[^/]*\.tsx$/.test("components/organisms/x/FooModal.tsx")).toBe(true);
  });
});
