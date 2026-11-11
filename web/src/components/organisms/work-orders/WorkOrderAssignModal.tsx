import { useState } from "react";
import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { TextField, TextAreaField, SelectField } from "@/components/molecules/Field";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { useTeams } from "@/services/teamService";
import { useAssignSurvey, type WorkOrder } from "@/services/workOrderService";

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

  const { data: teams = [] } = useTeams();
  const assignMutation = useAssignSurvey(workOrder?.work_order_id || "");

  if (!workOrder) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!leadTeamId) {
      toast.error("Pilih tim survei terlebih dahulu");
      return;
    }

    try {
      await assignMutation.mutateAsync({
        lead_team_id: leadTeamId,
        survey_date: surveyDate || undefined,
        notes: notes.trim() || undefined,
      });
      toast.success(`Tim survei berhasil ditugaskan untuk WO ${workOrder.wo_number}`);
      onClose();
    } catch {
      toast.error("Gagal menugaskan tim survei");
    }
  };

  return (
    <VmsDialog
      open={Boolean(workOrder)}
      onClose={onClose}
      title={`Tugaskan Tim Survei — ${workOrder.wo_number}`}
      size="lg"
    >
      <FormBlock onSubmit={handleSubmit} noValidate className="space-y-4 pt-2">
        <div className="bg-surface-elevated/50 p-3 rounded-lg border border-border/50 text-sm space-y-1">
          <TextBlock className="font-semibold text-ink">{workOrder.title}</TextBlock>
          <div className="text-muted-foreground text-xs">
            <TextBlock as="span">Klien: </TextBlock>
            <TextBlock as="span" className="text-ink font-medium">{workOrder.client_name}</TextBlock>
            <TextBlock as="span"> | Lokasi: </TextBlock>
            <TextBlock as="span" className="text-ink font-medium">
              {workOrder.site_name || "Kantor Pusat / Umum"}
            </TextBlock>
          </div>
        </div>

        <div className="space-y-3">
          <SelectField
            label="Pilih tim survei *"
            value={leadTeamId}
            onChange={(e) => setLeadTeamId(e.target.value)}
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
    </VmsDialog>
  );
}
