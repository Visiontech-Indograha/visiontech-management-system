import { useState } from "react";
import { toast } from "sonner";
import { DialogActions } from "@/components/molecules/DialogActions";
import { SelectField, TextField } from "@/components/molecules/Field";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { itemPayload, longDate } from "@/lib/alokasi";
import { errorMessage } from "@/lib/errors";
import type { DailyFormOptions } from "@/services/dailyPlanService";
import { useActivateStandby, useOrderSchedule } from "@/services/alokasiService";
import { useWorkTypes } from "@/services/workTypeService";

/** Sel SIAGA → "Ubah jadi pekerjaan": pilih order, template, judul, target; API mengaktifkan jadwal (SIAGA → WORK). */
export function ActivateStandbyDialog({ plan, divisionId, orders, onClose }: {
  plan: { daily_plan_id: string; team_name: string; work_date: string };
  divisionId: string;
  orders: DailyFormOptions["orders"];
  onClose: () => void;
}) {
  const [completionId, setCompletionId] = useState("");
  const [workTypeId, setWorkTypeId] = useState("");
  const [title, setTitle] = useState("");
  const [target, setTarget] = useState("1");
  const [location, setLocation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const activate = useActivateStandby();
  const schedule = useOrderSchedule(completionId);
  const types = useWorkTypes(false, divisionId).data?.filter((w) => w.kind !== "SURVEY_POINT") ?? [];
  const orderOptions = orders.filter((o) => !o.division_id || o.division_id === divisionId);
  const targetNum = Number(target.replace(",", "."));
  const dirty = completionId !== "" || workTypeId !== "" || title !== "" || location !== "" || target !== "1";

  const submit = async () => {
    if (!completionId) return setError("Pilih order klien.");
    if (!workTypeId) return setError("Pilih jenis pekerjaan (template).");
    if (title.trim().length < 3) return setError("Judul pekerjaan minimal 3 karakter.");
    if (!(targetNum > 0)) return setError("Target harus lebih dari 0.");
    setError(null);
    try {
      await activate.mutateAsync({
        id: plan.daily_plan_id,
        items: [itemPayload({ workTypeId, title, completionId, target: targetNum, location })],
      });
      toast.success("Siaga diubah menjadi pekerjaan.");
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const s = schedule.data;
  return (
    <VmsDialog
      open
      title="Ubah SIAGA jadi pekerjaan"
      onClose={onClose}
      dirty={dirty}
      footer={<DialogActions onCancel={onClose} busy={activate.isPending} formId="aktivasi-siaga-form"
                             submitLabel="Ubah jadi pekerjaan" busyLabel="Menyimpan..." />}
    >
      <FormBlock id="aktivasi-siaga-form" className="space-y-4" noValidate
                 onSubmit={(e) => { e.preventDefault(); void submit(); }}>
        <TextBlock className="text-sm">{plan.team_name}, {longDate(plan.work_date)}</TextBlock>
        <SelectField label="Order klien" value={completionId} onChange={(e) => setCompletionId(e.target.value)}>
          <ControlOption value="">Pilih order</ControlOption>
          {orderOptions.map((o) => (
            <ControlOption key={o.completion_id} value={o.completion_id}>
              {o.client_name} — {o.project_title}{o.order_number ? ` (${o.order_number})` : ""}
            </ControlOption>
          ))}
        </SelectField>
        {completionId && (
          <TextBlock role="status" className="text-sm">
            {s ? `Sisa belum dijadwalkan: ${s.unscheduled_target_qty} dari total ${s.total_target_unit}.` : "Memuat sisa target order..."}
          </TextBlock>
        )}
        <SelectField label="Jenis pekerjaan (template)" value={workTypeId} onChange={(e) => setWorkTypeId(e.target.value)}>
          <ControlOption value="">Pilih template</ControlOption>
          {types.map((w) => <ControlOption key={w.id} value={w.id}>{w.name}</ControlOption>)}
        </SelectField>
        <TextField label="Judul pekerjaan" value={title} onChange={(e) => setTitle(e.target.value)} />
        <TextField label="Target" inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} />
        <TextField label="Lokasi (opsional)" value={location} onChange={(e) => setLocation(e.target.value)} />
        <FormErrorText message={error} />
      </FormBlock>
    </VmsDialog>
  );
}
