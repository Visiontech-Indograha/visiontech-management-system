// Penegak statis aturan desain web R1-R15 (docs/ATURAN-DESAIN-WEB.md). TIDAK mengubah perilaku UI.
// Setiap aturan punya baseline per berkas (jumlah pelanggaran lama). Pelanggaran BARU atau tambahan gagal;
// bila pelanggaran berkurang, perbarui angka baseline ke nilai baru (tes gagal sampai diperbarui: baseline hanya menyusut).
import { describe, expect, it } from "vitest";

const RAW = import.meta.glob<string>("/src/**/*.{ts,tsx}", { query: "?raw", import: "default", eager: true });
const SUMBER: Record<string, string> = {};
for (const [k, v] of Object.entries(RAW)) {
  const f = k.slice("/src/".length);
  if (/\.test\.tsx?$/.test(f) || f.startsWith("test/") || f.endsWith("apiTypes.ts")) continue;
  SUMBER[f] = v;
}

type Jenis = "ts" | "tsx" | "fmt";
interface Aturan { id: string; aturan: string; re: RegExp; jenis: Jenis; baseline: Record<string, number> }

const cocok = (f: string, j: Jenis) => (j === "tsx" ? f.endsWith(".tsx") : j === "fmt" ? f !== "lib/format.ts" : true);
export function hitung(a: Pick<Aturan, "re" | "jenis">, sumber: Record<string, string>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [f, teks] of Object.entries(sumber)) {
    if (!cocok(f, a.jenis)) continue;
    const n = (teks.match(a.re) ?? []).length;
    if (n) out[f] = n;
  }
  return out;
}
/** Bandingkan hasil hitung dengan baseline: [naik, turun]. */
export function banding(hasil: Record<string, number>, baseline: Record<string, number>) {
  const naik = Object.entries(hasil).filter(([f, n]) => n > (baseline[f] ?? 0)).map(([f, n]) => `${f}: ${n} > ${baseline[f] ?? 0}`);
  const turun = Object.entries(baseline).filter(([f, n]) => (hasil[f] ?? 0) < n).map(([f, n]) => `${f}: ${hasil[f] ?? 0} < ${n}`);
  return { naik, turun };
}

const ATURAN: Aturan[] = [
  { id: "R1", aturan: "Tombol kirim: pakai prop pending, bukan disabled={x.isPending} manual", re: /disabled=\{[^}]*isPending/g, jenis: "tsx", baseline: {
    "components/molecules/FilePreview.tsx": 1,
    "components/organisms/account/AccountSessionsPanel.tsx": 2,
    "components/organisms/account/AccountSummaryCard.tsx": 2,
    "components/organisms/assets/AssetStatusDialog.tsx": 1,
    "components/organisms/assets/LoanRequestsPanel.tsx": 2,
    "components/organisms/clients/ClientDeactivateDialog.tsx": 1,
    "components/organisms/clients/ClientSitesModal.tsx": 2,
    "components/organisms/directory/AccountCard.tsx": 5,
    "components/organisms/directory/AccountDevicesAdmin.tsx": 3,
    "components/organisms/directory/AccountLoginEditForm.tsx": 1,
    "components/organisms/directory/DocumentsPanel.tsx": 2,
    "components/organisms/directory/EmployeeAddressesPanel.tsx": 2,
    "components/organisms/directory/EmployeeFaceCard.tsx": 3,
    "components/organisms/hse/HseCampaignsPanel.tsx": 3,
    "components/organisms/leaves/CancelLeaveDialog.tsx": 1,
    "components/organisms/leaves/LeaveReviewDialog.tsx": 3,
    "components/organisms/mess/MessRequestList.tsx": 1,
    "components/organisms/monitoring/OvertimeReviewList.tsx": 3,
    "components/organisms/offboarding/OffboardingDetailDialog.tsx": 4,
    "components/organisms/offboarding/OffboardingFormDialog.tsx": 1,
    "components/organisms/projects/ProjectDeleteDialog.tsx": 1,
    "components/organisms/surveys/SurveyBomPanel.tsx": 1,
    "components/organisms/surveys/SurveyLogoPanel.tsx": 2,
    "components/organisms/surveys/SurveyReviewBar.tsx": 2,
    "components/organisms/teams/TeamDetailDialog.tsx": 2,
    "components/organisms/work-completions/PmSignatureDialog.tsx": 1,
    "components/organisms/work-completions/WorkCompletionBomTable.tsx": 2,
    "components/organisms/work-completions/WorkCompletionExportPanel.tsx": 1,
    "components/organisms/work-completions/WorkCompletionList.tsx": 1,
    "components/organisms/work-orders/WorkOrderAssignModal.tsx": 2,
    "components/organisms/work-orders/WorkOrderBastModal.tsx": 2,
    "components/organisms/work-orders/WorkOrderCreateModal.tsx": 2,
    "components/organisms/work-plans/CorrectionsPanel.tsx": 3,
    "components/organisms/work-plans/DailyItemsPanel.tsx": 4,
    "components/organisms/work-plans/DailyPlanDetailDialog.tsx": 6,
    "components/organisms/work-plans/DailyPlanLocationForm.tsx": 2,
    "components/organisms/work-plans/DailyWeekToolbar.tsx": 2,
    "components/organisms/work-types/WorkTypeCopyDialog.tsx": 2,
    "components/organisms/work-types/WorkTypeDeactivateDialog.tsx": 2,
  } },
  { id: "R3", aturan: "Setiap catch memakai variabel galat dan errorMessage(err, cadangan): catch tanpa parameter", re: /catch\s*\{/g, jenis: "ts", baseline: {
    "components/molecules/SignaturePad.tsx": 1,
    "hooks/useLiveEvents.ts": 3,
    "lib/apiClient.ts": 2,
    "lib/tabSync.ts": 3,
    "stores/sessionStore.ts": 3,
  } },
  { id: "R3b", aturan: "Pesan galat bukan String(err)/kode mentah", re: /toast\.error\(\s*(String\(|[a-zA-Z]+\.(code|status)\b)/g, jenis: "ts", baseline: {} },
  { id: "R4", aturan: "Validasi di kolom (Field), bukan toast: toast.error berliteral", re: /toast\.error\(\s*["`']/g, jenis: "ts", baseline: {
    "components/organisms/clients/ClientSitesModal.tsx": 7,
    "components/organisms/directory/AccountCard.tsx": 1,
    "components/organisms/directory/EmployeeAddressesPanel.tsx": 2,
    "components/organisms/hse/HseCampaignsPanel.tsx": 1,
    "components/organisms/offboarding/OffboardingDetailDialog.tsx": 1,
    "components/organisms/surveys/SurveyBomPanel.tsx": 1,
    "components/organisms/surveys/SurveyPlanDialog.tsx": 1,
    "components/organisms/surveys/SurveyReviewBar.tsx": 1,
    "components/organisms/work-orders/WorkOrderBastModal.tsx": 2,
    "components/organisms/work-orders/WorkOrderCreateModal.tsx": 3,
    "components/organisms/work-plans/DailyWeekMatrix.tsx": 1,
    "components/organisms/work-types/WorkTypeCopyDialog.tsx": 1,
  } },
  { id: "R5", aturan: "Unggahan lewat UploadField: type=\"file\" langsung", re: /type="file"/g, jenis: "tsx", baseline: {
    "components/organisms/account/AccountSummaryCard.tsx": 1,
    "components/organisms/assets/AssetLendDialog.tsx": 1,
    "components/organisms/assets/VehicleFilesDialog.tsx": 1,
    "components/organisms/directory/DocumentsPanel.tsx": 1,
    "components/organisms/directory/EmployeeCreateDialog.tsx": 1,
    "components/organisms/directory/EmployeeProfileDialog.tsx": 1,
    "components/organisms/hse/HseCampaignPhotosField.tsx": 1,
    "components/organisms/leaves/LeaveApplyDialog.tsx": 1,
    "components/organisms/offboarding/OffboardingDetailDialog.tsx": 1,
    "components/organisms/surveys/SurveyLogoPanel.tsx": 1,
    "components/organisms/work-types/WorkTypeFormDialog.tsx": 1,
  } },
  { id: "R7", aturan: "Sentence case: label/placeholder/title berformat Title Case", re: /\b(label|placeholder|title)="[A-Z][a-z]+( [A-Z][a-z]+)+"/g, jenis: "tsx", baseline: {
    "components/organisms/clients/ClientFormDialog.tsx": 2,
    "components/organisms/clients/ClientSitesModal.tsx": 2,
    "components/organisms/leaves/CancelLeaveDialog.tsx": 2,
    "components/organisms/leaves/LeaveApplyDialog.tsx": 3,
    "components/organisms/media/ImageLightboxModal.tsx": 1,
    "components/organisms/mess/MessFormDialog.tsx": 2,
    "components/organisms/mess/MessPlaceFormDialog.tsx": 2,
    "components/organisms/projects/ProjectFormDialog.tsx": 7,
    "components/organisms/work-completions/PmSignatureDialog.tsx": 1,
    "components/organisms/work-completions/WorkCompletionBomTable.tsx": 5,
    "components/organisms/work-completions/WorkCompletionFormDialog.tsx": 4,
    "components/organisms/work-orders/WorkOrderCreateModal.tsx": 1,
    "components/organisms/work-plans/WeeklyPresentationDialog.tsx": 1,
    "components/organisms/work-types/WorkTypeMaterialsDialog.tsx": 4,
    "components/templates/mess/MessTemplate.tsx": 2,
    "components/templates/teams/TeamsTemplate.tsx": 1,
    "components/templates/work-orders/WorkOrdersTemplate.tsx": 1,
  } },
  { id: "R8a", aturan: "Tanggal/angka lewat lib/format.ts: toLocale*String di luar format.ts", re: /toLocale\w*String/g, jenis: "fmt", baseline: {
    "components/organisms/attendance/AttendanceList.tsx": 1,
    "components/organisms/attendance/SelfieCaptureDialog.tsx": 1,
    "components/organisms/monitoring/AttendanceRecordHistory.tsx": 1,
    "components/organisms/projects/ProjectList.tsx": 1,
    "components/organisms/work-completions/WorkCompletionDetailModal.tsx": 2,
  } },
  { id: "R8b", aturan: "Uang lewat formatRupiah: literal `Rp ${`", re: /Rp \$\{/g, jenis: "ts", baseline: {
    "components/organisms/attendance/AttendanceList.tsx": 1,
  } },
  { id: "R10", aturan: "Pilihan \"Pilih ...\" tanpa tanda \"--\"", re: /["`'>]-- ?[A-Za-z]/g, jenis: "tsx", baseline: {
    "components/organisms/leaves/LeaveList.tsx": 1,
    "components/organisms/mess/MessFormDialog.tsx": 2,
    "components/organisms/projects/ProjectFormDialog.tsx": 3,
    "components/organisms/projects/ProjectList.tsx": 3,
    "components/organisms/work-completions/WorkCompletionFormDialog.tsx": 3,
    "components/organisms/work-orders/WorkOrderAssignModal.tsx": 1,
  } },
];

/** R2: berkas yang memanggil hapus/nonaktifkan harus memakai konfirmasi. Baseline = daftar berkas lama. */
const DEL_RE = /\buse(Delete|Remove|Deactivate)\w*\s*\(|\bdelete[A-Z]\w*\s*\(/;
const KONFIRMASI_RE = /ConfirmDialog|DeleteConfirmButton|useUndoableDelete/;
const R2_BASELINE: string[] = [
  "components/organisms/assets/AssetStatusDialog.tsx",
  "components/organisms/clients/ClientDeactivateDialog.tsx",
  "components/organisms/directory/DocumentsPanel.tsx",
  "components/organisms/divisions/MasterRemoveDialog.tsx",
  "components/organisms/projects/ProjectDeleteDialog.tsx",
  "components/organisms/teams/TeamDetailDialog.tsx",
  "components/organisms/work-completions/WorkCompletionList.tsx",
  "components/organisms/work-types/WorkTypeDeactivateDialog.tsx",
  "pages/teams/TeamsPage.tsx",
];
export const hapusTanpaKonfirmasi = (sumber: Record<string, string>) =>
  Object.keys(sumber).filter((f) => f.endsWith(".tsx") && /^(components|pages)\//.test(f) && DEL_RE.test(sumber[f]) && !KONFIRMASI_RE.test(sumber[f])).sort();

describe("aturan desain web (penegak statis dengan baseline)", () => {
  for (const a of ATURAN) {
    it(`${a.id}: ${a.aturan}`, () => {
      const { naik, turun } = banding(hitung(a, SUMBER), a.baseline);
      expect(naik, `Pelanggaran baru atau bertambah (${a.id}). Perbaiki, jangan menambah baseline.`).toEqual([]);
      expect(turun, `Pelanggaran berkurang: turunkan/hapus angka baseline ${a.id} di aturanDesain.test.ts`).toEqual([]);
    });
  }

  it("R2: aksi hapus/nonaktifkan lewat konfirmasi (ConfirmDialog, DeleteConfirmButton, useUndoableDelete)", () => {
    const sekarang = hapusTanpaKonfirmasi(SUMBER);
    expect(sekarang.filter((f) => !R2_BASELINE.includes(f)), "Berkas baru memanggil hapus tanpa konfirmasi").toEqual([]);
    expect(R2_BASELINE.filter((f) => !sekarang.includes(f)), "Hapus dari R2_BASELINE (sudah benar/hilang)").toEqual([]);
  });

  describe("kasus uji penegak (contoh pelanggar harus terdeteksi)", () => {
    const contoh = (id: string) => ATURAN.find((a) => a.id === id)!;
    it("mendeteksi pelanggaran contoh", () => {
      const s = {
        "components/organisms/x/Contoh.tsx": [
          '<Button disabled={m.isPending}>Simpan</Button>',
          "try { a() } catch { toast.error(\"Gagal\") }",
          '<input type="file" />',
          '<Field label="Nama Lengkap" />',
          'new Date().toLocaleDateString("id-ID")',
          '`Rp ${n}`',
          '<option value="">-- Pilih</option>',
          "const x = deleteThing(1)",
        ].join("\n"),
      };
      for (const id of ["R1", "R3", "R4", "R5", "R7", "R8a", "R8b", "R10"]) {
        expect(Object.keys(hitung(contoh(id), s)), id).toEqual(["components/organisms/x/Contoh.tsx"]);
      }
      expect(hapusTanpaKonfirmasi(s)).toEqual(["components/organisms/x/Contoh.tsx"]);
      expect(hapusTanpaKonfirmasi({ "components/a/B.tsx": 'import {ConfirmDialog} from "x"; deleteThing(1)' })).toEqual([]);
    });
    it("bukan pelanggaran: teks biasa dan toLocale di lib/format.ts", () => {
      const s = { "lib/format.ts": "d.toLocaleDateString()", "components/a/B.tsx": '<Field label="Nama lengkap" />' };
      expect(hitung(contoh("R8a"), s)).toEqual({});
      expect(hitung(contoh("R7"), s)).toEqual({});
    });
  });
});
