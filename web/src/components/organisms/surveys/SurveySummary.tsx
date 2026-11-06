import { Pill } from "@/components/molecules/Pill";
import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDate } from "@/lib/format";
import { SURVEY_STATE_LABEL, type Survey } from "@/services/surveyService";

const TONE = { SUBMITTED: "warning", DRAFT: "info", APPROVED: "success" } as const;

const NEXT: Record<Survey["state"], string> = {
  DRAFT: "Ketua tim sedang mengisi titik di aplikasi HP. Anda tetap bisa melihat pratinjau laporannya.",
  SUBMITTED: "Periksa titik dan foto serta pratinjau laporan, lalu Setujui atau Kembalikan dengan catatan.",
  APPROVED: "Survei disetujui. Unduh laporan resmi dan rencanakan pemasangan dari survei ini.",
};

/** Ringkasan survei: status + langkah berikutnya, info tim, jumlah titik. */
export function SurveySummary({ survey: s }: { survey: Survey }) {
  const needs = new Set(s.points.flatMap((p) => p.lines.filter((l) => l.category === "KEBUTUHAN").map((l) => l.name)));
  return (
    <section aria-label="Ringkasan survei" className="mb-6 grid gap-4 rounded-panel border border-line bg-surface p-4 shadow-card md:grid-cols-4">
      <div className="md:col-span-2">
        <Pill tone={TONE[s.state]}>{SURVEY_STATE_LABEL[s.state]}</Pill>
        <TextBlock className="mt-2 text-sm">{NEXT[s.state]}</TextBlock>
        {s.review_note && s.state === "DRAFT" && (
          <TextBlock className="mt-1 text-xs text-warning">{`Catatan pengembalian: ${s.review_note}`}</TextBlock>
        )}
      </div>
      <div>
        <TextBlock className="text-xs uppercase text-mist">Tim · tanggal</TextBlock>
        <TextBlock className="text-sm font-medium">{s.team_name ?? "-"}</TextBlock>
        <TextBlock className="text-xs text-mist">{`${formatDate(s.work_date)} · ${s.work_type_name}`}</TextBlock>
      </div>
      <div>
        <TextBlock className="text-xs uppercase text-mist">Titik · kebutuhan</TextBlock>
        <TextBlock className="text-sm font-medium">{`${s.points.length} titik · ${s.bom.length} jenis material`}</TextBlock>
        <TextBlock className="text-xs text-mist">{needs.size ? [...needs].join(", ") : "Tanpa kebutuhan khusus"}</TextBlock>
      </div>
    </section>
  );
}
