import { useState } from "react";
import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { TextField, TextAreaField, SelectField } from "@/components/molecules/Field";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { useTeams } from "@/services/teamService";
import { useAssignSurvey, type WorkOrder } from "@/services/workOrderService";

export const SURVEY_DATE_REQUIRED =
  "Tanggal survei wajib diisi agar tim bisa melihat tugasnya di HP.";

interface WorkOrderAssignModalProps {
  workOrder: WorkOrder | null;
  onClose: () => void;
}

export function WorkOrderAssignModal({
  workOrder,
  onClose,
}: WorkOrderAssignModalProps) {
  const [leadTeamId, setLeadTeamId] = useState(workOrder?.lead_team_id || "");
  const [surveyDate, setSurveyDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [notes, setNotes] = useState("");
  const [dateError, setDateError] = useState("");
  const [teamError, setTeamError] = useState("");
  const [summary, setSummary] = useState("");

  const { data: teams = [] } = useTeams();
  const assignMutation = useAssignSurvey(workOrder?.work_order_id || "");

  if (!workOrder) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setDateError("");
    setTeamError("");
    if (!leadTeamId) {
      setTeamError("Pilih tim survei terlebih dahulu.");
      return;
    }
    if (!surveyDate) {
      setDateError(SURVEY_DATE_REQUIRED);
      return;
    }

    try {
      const result = await assignMutation.mutateAsync({
        lead_team_id: leadTeamId,
        survey_date: surveyDate,
        notes: notes.trim() || undefined,
      });
      toast.success(`Tim survei berhasil ditugaskan untuk WO ${workOrder.wo_number}`);
      setSummary(result.survey_assignment_summary || "");
      if (!result.survey_assignment_summary) onClose();
    } catch (err) {
      const setField = (name: string, e: { message: string }) => {
        if (name === "survey_date") setDateError(e.message);
        else if (name === "lead_team_id") setTeamError(e.message);
      };
      if (!applyFieldErrors(err, setField as never, ["survey_date", "lead_team_id"])) {
        toast.error(errorMessage(err, "Gagal menugaskan tim survei"));
      }
    }
  };

  return (
    <VmsDialog
      open={Boolean(workOrder)}
      onClose={onClose}
      title={`Tugaskan Tim Survei — ${workOrder.wo_number}`}
      size="lg"
    >
      {summary ? (
        <div className="space-y-4 pt-2">
          <TextBlock role="status" className="rounded-lg border border-border bg-surface-elevated p-3 text-sm text-ink">
            {summary}
          </TextBlock>
          <div className="flex justify-end">
            <ActionButton type="button" variant="default" onClick={onClose}>
              <TextBlock as="span">Selesai</TextBlock>
            </ActionButton>
          </div>
        </div>
      ) : (
      <FormBlock onSubmit={handleSubmit} noValidate className="space-y-4 pt-2">
        <div className="bg-surface-elevated/50 p-3 rounded-lg border border-border/50 text-sm space-y-1">
          <TextBlock className="font-semibold text-ink">{workOrder.title}</TextBlock>
          <div className="text-muted-foreground text-xs">
            <TextBlock as="span">Klien: </TextBlock>
            <TextBlock as="span" className="text-ink font-medium">{workOrder.client_name}</TextBlock>
            <TextBlock as="span"> | Lokasi: </TextBlock>
            <TextBlock as="span" className="text-ink font-medium">
              {workOrder.site_name || "Belum ada site"}
            </TextBlock>
          </div>
        </div>

        <div className="space-y-3">
          <SelectField
            label="Pilih tim survei *"
            value={leadTeamId}
            onChange={(e) => setLeadTeamId(e.target.value)}
            error={teamError || undefined}
            required
          >
            <ControlOption value="">-- Pilih Tim Lapangan --</ControlOption>
            {teams.map((t) => (
              <ControlOption key={t.team_id} value={t.team_id}>
                {t.name} (Ketua: {t.leader_name || "Tanpa Ketua"})
              </ControlOption>
            ))}
          </SelectField>

          <TextField
            label="Tanggal survei di lapangan *"
            type="date"
            value={surveyDate}
            onChange={(e) => setSurveyDate(e.target.value)}
            error={dateError || undefined}
            required
          />

          <TextAreaField
            label="Instruksi Khusus untuk Tim Survei"
            placeholder="Misal: Cek ketersediaan jalur kabel, bawa tangga 6 meter, hubungi PIC Pak Budi..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
          />
        </div>

        <div className="flex justify-end gap-2 pt-3 border-t border-border">
          <ActionButton
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={assignMutation.isPending}
          >
            <TextBlock as="span">Batal</TextBlock>
          </ActionButton>
          <ActionButton
            type="submit"
            variant="default"
            disabled={assignMutation.isPending}
          >
            <TextBlock as="span">
              {assignMutation.isPending ? "Menugaskan..." : "Tugaskan Tim Survei"}
            </TextBlock>
          </ActionButton>
        </div>
      </FormBlock>
      )}
    </VmsDialog>
  );
}
