import { TextBlock } from "@/components/molecules/TextBlock";
import { formatDate } from "@/lib/format";
import type { ScheduledSurvey } from "@/services/dailyPlanService";

/** Survei work order yang ditugaskan pada minggu yang sedang dilihat (tanggal, tim, lokasi). Kosong = tidak tampil. */
export function WeekSurveysPanel({ surveys }: { surveys: ScheduledSurvey[] }) {
  if (!surveys.length) return null;
  return (
    <section aria-label="Survei dijadwalkan minggu ini" className="mb-4 flex flex-col gap-2 rounded-panel border border-line bg-surface p-4 shadow-card">
      <TextBlock as="h2" className="text-sm font-semibold">Survei dijadwalkan minggu ini ({surveys.length})</TextBlock>
      {surveys.map((s) => (
        <div key={s.survey_id} className="text-sm">
          <TextBlock as="strong" className="font-medium">
            {formatDate(String(s.survey_date))} · {s.wo_number} · {s.title}
          </TextBlock>
          <TextBlock className="text-mist">
            Tim {s.surveyor_team_name ?? "belum dipilih"}
            {s.client_name ? ` · ${s.client_name}` : ""}
            {s.site_name ? ` · ${s.site_name}` : ""}
          </TextBlock>
        </div>
      ))}
    </section>
  );
}
