import { useMemo, useState } from "react";
import { toast } from "sonner";
import { CheckControl } from "@/components/molecules/CheckControl";
import { DialogActions } from "@/components/molecules/DialogActions";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlLabel, ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { addDays, useDailyPlans } from "@/services/dailyPlanService";
import { usePlanFromSurvey, type Survey } from "@/services/surveyService";
import { useWorkTypes } from "@/services/workTypeService";

const OPEN = ["DRAFT", "SUBMITTED"];

/** Rencana lanjutan dari survei yang disetujui: pilih tanggal (jadwal DRAFT tim dibuat otomatis bila belum ada,
 * atau ditambahkan ke jadwal DRAFT/SUBMITTED yang sudah ada), jenis pekerjaan pemasangan, opsional jenis
 * persiapan untuk titik yang punya kebutuhan (scaffolding, tangga, izin …), dan titiknya. */
export function SurveyPlanDialog({ survey, onClose }: { survey: Survey; onClose: () => void }) {
  const plans = useDailyPlans({ start: survey.work_date, end: addDays(survey.work_date, 60), division_id: survey.division_id });
  const workTypes = useWorkTypes(false, survey.division_id);
  const plan = usePlanFromSurvey(survey.task_id);
  const teamDays = useMemo(
    () => new Map((plans.data ?? []).filter((p) => p.team_name === survey.team_name).map((p) => [p.work_date, p])),
    [plans.data, survey.team_name],
  );
  // Default: hari pertama setelah survei yang belum terbit (paket 7 hari sudah terbit → hari sesudahnya).
  const firstFree = useMemo(() => {
    let d = addDays(survey.work_date, 1);
    for (let i = 0; i < 60; i++) {
      const p = teamDays.get(d);
      if (!p || OPEN.includes(p.status)) break;
      d = addDays(d, 1);
    }
    return d;
  }, [survey.work_date, teamDays]);
  const installTypes = (workTypes.data ?? []).filter((w) => w.id !== survey.work_type_id);
  const [picked, setPicked] = useState<string | null>(null);
  const [typeId, setTypeId] = useState("");
  const [prepTypeId, setPrepTypeId] = useState("");
  const [points, setPoints] = useState<string[]>(survey.points.map((p) => p.point_id));
  const day = picked ?? firstFree;
  const existing = teamDays.get(day);
  const blocked = !!existing && !OPEN.includes(existing.status);
  const team = survey.team_name ?? "tim";

  const submit = async () => {
    if (blocked) return toast.error("Jadwal tim di tanggal itu sudah terbit. Pilih tanggal lain.");
    try {
      const res = await plan.mutateAsync({
        work_date: day,
        work_type_id: typeId || null,
        task_phase: "INSTALLATION",
        point_ids: points,
        preparation_work_type_id: prepTypeId || null,
      });
      toast.success(
        `${res.created_item_ids.length} item ditambahkan ke jadwal ${formatDate(day)}. Cek lalu kirim ke tim di menu Jadwal harian.`,
      );
      onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <VmsDialog
      open
      title="Rencanakan pekerjaan dari survei"
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={plan.isPending} formId="survey-plan-form" submitLabel="Buat item" />}
    >
      <FormBlock
        id="survey-plan-form"
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <TextField
          label="Tanggal pekerjaan lanjutan"
          type="date"
          min={survey.work_date}
          value={day}
          onChange={(e) => setPicked(e.target.value || null)}
        />
        <TextBlock className={`text-xs ${blocked ? "text-danger" : "text-mist"}`}>
          {blocked
            ? `Jadwal ${team} pada ${formatDate(day)} sudah terbit (${existing.status}). Pilih tanggal lain.`
            : existing
              ? `Ditambahkan ke jadwal ${existing.status} yang sudah ada (${existing.site_name || "lokasi belum ditentukan"}).`
              : `Belum ada jadwal ${team} di tanggal ini — jadwal DRAFT baru dibuat otomatis (lokasi & jam disalin dari hari survei).`}
        </TextBlock>
        <SelectField label="Jenis pekerjaan pemasangan" value={typeId} onChange={(e) => setTypeId(e.target.value)}>
          <ControlOption value="">Bawaan tiap jenis titik (otomatis)</ControlOption>
          {installTypes.map((w) => (
            <ControlOption key={w.id} value={w.id}>{w.name}</ControlOption>
          ))}
        </SelectField>
        {!workTypes.isPending && installTypes.length === 0 && (
          <TextBlock className="text-xs text-warning">
            Divisi ini belum punya jenis pekerjaan pemasangan. Buat dulu di menu Jenis pekerjaan.
          </TextBlock>
        )}
        <SelectField
          label="Persiapan untuk titik berkebutuhan (opsional)"
          value={prepTypeId}
          onChange={(e) => setPrepTypeId(e.target.value)}
        >
          <ControlOption value="">Tanpa item persiapan</ControlOption>
          {installTypes.map((w) => (
            <ControlOption key={w.id} value={w.id}>{w.name}</ControlOption>
          ))}
        </SelectField>
        <div className="space-y-2">
          <TextBlock className="text-sm font-medium">Titik yang direncanakan</TextBlock>
          {survey.points.map((p) => {
            const needs = p.lines.filter((l) => l.category === "KEBUTUHAN").map((l) => l.name);
            return (
              <ControlLabel key={p.point_id} className="flex items-start gap-2 text-sm">
                <CheckControl
                  checked={points.includes(p.point_id)}
                  onCheckedChange={(on) =>
                    setPoints((cur) => (on ? [...cur, p.point_id] : cur.filter((x) => x !== p.point_id)))
                  }
                />
                <div>
                  <TextBlock>{p.name}</TextBlock>
                  {needs.length > 0 && <TextBlock className="text-xs text-mist">{`Kebutuhan: ${needs.join(", ")}`}</TextBlock>}
                </div>
              </ControlLabel>
            );
          })}
        </div>
      </FormBlock>
    </VmsDialog>
  );
}
