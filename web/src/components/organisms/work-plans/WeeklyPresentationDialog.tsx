import { useState } from "react";
import { AlertCircle, Calendar, Camera, CheckCircle2, Users } from "@/components/molecules/Glyphs";
import { ActionButton } from "@/components/molecules/ActionButton";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { formatDate } from "@/lib/format";
import { useWeeklyPresentation } from "@/services/dailyPlanService";

interface TeamOption {
  team_id: string;
  name: string;
  leader_name?: string | null;
}

export function WeeklyPresentationDialog({
  open,
  onClose,
  teams,
  initialDate,
}: {
  open: boolean;
  onClose: () => void;
  teams: TeamOption[];
  initialDate: string;
}) {
  const [selectedTeamId, setSelectedTeamId] = useState<string>(() => teams[0]?.team_id || "");
  const [meetingDate, setMeetingDate] = useState<string>(initialDate);

  const { data, isLoading, isError, error } = useWeeklyPresentation(selectedTeamId, meetingDate);

  if (!open) return null;

  return (
    <VmsDialog
      open={open}
      onClose={onClose}
      title="Presentasi Evaluasi Mingguan (Sabtu)"
      className="max-w-3xl"
    >
      <div className="space-y-4">
        <TextBlock as="p" className="text-xs text-mist">
          Rekapitulasi laporan harian tim lapangan selama satu minggu untuk evaluasi meeting mingguan setiap Sabtu.
        </TextBlock>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-muted/30 p-3 rounded-lg border border-line">
          <SelectField
            label="Pilih Tim"
            value={selectedTeamId}
            onChange={(e) => setSelectedTeamId(e.target.value)}
          >
            {teams.map((t) => (
              <ControlOption key={t.team_id} value={t.team_id}>
                {t.name} {t.leader_name ? `(${t.leader_name})` : ""}
              </ControlOption>
            ))}
          </SelectField>

          <TextField
            label="Tanggal Meeting (Sabtu)"
            type="date"
            value={meetingDate}
            onChange={(e) => setMeetingDate(e.target.value)}
          />
        </div>

        {teams.length === 0 && (
          <div className="p-6 text-center border border-dashed border-line rounded-lg">
            <TextBlock as="span" className="text-sm text-mist">
              Belum ada tim lapangan yang terdaftar pada divisi ini.
            </TextBlock>
          </div>
        )}

        {isLoading && (
          <div className="py-8 text-center">
            <TextBlock as="span" className="text-sm text-mist animate-pulse">
              Memuat rekap presentasi mingguan...
            </TextBlock>
          </div>
        )}

        {isError && (
          <div className="p-3 bg-danger/10 border border-danger/20 rounded-md flex items-center gap-2">
            <AlertCircle size={16} className="text-danger shrink-0" />
            <TextBlock as="span" className="text-sm text-danger">
              Gagal memuat rekap presentasi: {(error as Error)?.message || "Terjadi kesalahan"}
            </TextBlock>
          </div>
        )}

        {data && !isLoading && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-card border border-line rounded-lg">
              <div className="flex items-center gap-2">
                <Users size={18} className="text-primary" />
                <TextBlock as="span" className="font-semibold text-charcoal dark:text-light">
                  {data.team_name || "Tim"}
                </TextBlock>
                <TextBlock as="span" className="text-xs text-mist">
                  {`· Progres: ${data.completed_plans} dari ${data.total_plans} jadwal selesai`}
                </TextBlock>
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar size={14} className="text-mist" />
                <TextBlock as="span" className="text-xs text-mist">
                  {`Periode: ${formatDate(data.week_start)} – ${formatDate(data.week_end)}`}
                </TextBlock>
              </div>
            </div>

            <div>
              <TextBlock as="h4" className="text-sm font-medium text-charcoal dark:text-light mb-2">
                {`Daftar Laporan Harian (${data.daily_reports.length} hari terlapor)`}
              </TextBlock>

              {data.daily_reports.length === 0 ? (
                <div className="p-6 text-center border border-dashed border-line rounded-lg">
                  <TextBlock as="span" className="text-sm text-mist">
                    Belum ada laporan harian yang diserahkan untuk periode minggu ini.
                  </TextBlock>
                </div>
              ) : (
                <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                  {data.daily_reports.map((rep) => (
                    <div
                      key={rep.report_id}
                      className="p-3 border border-line rounded-lg bg-surface/40 hover:bg-surface/80 transition-colors"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <TextBlock as="span" className="text-xs font-semibold text-primary">
                          {formatDate(rep.submitted_at || rep.create_at)}
                        </TextBlock>
                        <div className="flex items-center gap-2">
                          {rep.photos_json && Array.isArray(rep.photos_json) && rep.photos_json.length > 0 && (
                            <div className="flex items-center gap-1">
                              <Camera size={12} className="text-mist" />
                              <TextBlock as="span" className="text-xs text-mist">
                                {`${rep.photos_json.length} foto`}
                              </TextBlock>
                            </div>
                          )}
                          <div className="flex items-center gap-1">
                            <CheckCircle2 size={12} className="text-success" />
                            <TextBlock as="span" className="text-xs text-success">
                              Terverifikasi
                            </TextBlock>
                          </div>
                        </div>
                      </div>

                      <TextBlock as="p" className="text-sm text-charcoal dark:text-light whitespace-pre-wrap">
                        {rep.summary}
                      </TextBlock>

                      {rep.obstacles && (
                        <div className="mt-2 bg-amber-500/10 border border-amber-500/20 rounded p-1.5 flex items-start gap-1.5">
                          <AlertCircle size={14} className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                          <div>
                            <TextBlock as="span" className="text-xs font-medium text-amber-600 dark:text-amber-400">
                              {"Kendala: "}
                            </TextBlock>
                            <TextBlock as="span" className="text-xs text-amber-600 dark:text-amber-400">
                              {rep.obstacles}
                            </TextBlock>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {(data.presentation_notes || data.pm_feedback) && (
              <div className="p-3 bg-muted/40 border border-line rounded-lg space-y-2">
                {data.presentation_notes && (
                  <div>
                    <TextBlock as="span" className="text-xs font-semibold text-mist uppercase tracking-wide">
                      Catatan Presentasi
                    </TextBlock>
                    <TextBlock as="p" className="text-sm text-charcoal dark:text-light mt-0.5">
                      {data.presentation_notes}
                    </TextBlock>
                  </div>
                )}
                {data.pm_feedback && (
                  <div>
                    <TextBlock as="span" className="text-xs font-semibold text-primary uppercase tracking-wide">
                      Feedback PM / Evaluasi
                    </TextBlock>
                    <TextBlock as="p" className="text-sm text-charcoal dark:text-light mt-0.5">
                      {data.pm_feedback}
                    </TextBlock>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end pt-3 border-t border-line">
          <ActionButton variant="outline" onClick={onClose}>
            Tutup
          </ActionButton>
        </div>
      </div>
    </VmsDialog>
  );
}
