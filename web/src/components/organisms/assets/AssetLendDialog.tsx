import { useState } from "react";
import { toast } from "sonner";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { errorMessage } from "@/lib/errors";
import { useLend, useAssetAvailability, type AssetKind } from "@/services/assetService";
import { useDailyPlans, wibDate } from "@/services/dailyPlanService";
import { useEmployees, useUploadFile } from "@/services/employeeService";
import { useTeams } from "@/services/teamService";
import { AssetFormDialog } from "./AssetFormDialog";

/**
 * Serah terima aset ke karyawan + foto bukti (opsional). Isian jadwal (tanggal, tim, jadwal harian) menentukan
 * ketersediaan: bila aset sudah dipakai tim lain pada tanggal itu, peringatan tampil dan simpan dinonaktifkan.
 * Aturan STNK/KIR/SIM & jadwal tetap dijaga API.
 */
export function AssetLendDialog({ kind, assetId, assetName, onClose, preset }: {
  kind: AssetKind;
  assetId: string;
  assetName: string;
  onClose: () => void;
  /** Isian awal dari jadwal harian (tombol di dialog jadwal): tanggal, tim, dan jadwal. */
  preset?: { workDate?: string; teamId?: string; dailyPlanId?: string };
}) {
  const lend = useLend();
  const upload = useUploadFile();
  const [q, setQ] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [workDate, setWorkDate] = useState(preset?.workDate || wibDate());
  const [teamId, setTeamId] = useState(preset?.teamId ?? "");
  const [dailyPlanId, setDailyPlanId] = useState(preset?.dailyPlanId ?? "");
  const employees = useEmployees({ q, status: "active", page: 1 });
  const teams = useTeams();
  const plans = useDailyPlans({ start: workDate, end: workDate });
  const availability = useAssetAvailability(workDate, teamId || undefined);
  const [formError, setFormError] = useState<string | null>(null);
  const busy = lend.isPending || upload.isPending;

  const row = availability.data?.find((r) => r.asset_id === assetId);
  const conflict = !!row?.used_by_team_id && !row.used_by_requested_team;
  const planOptions = (plans.data ?? []).filter((p) => !teamId || p.team_id === teamId);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    if (!employeeId) return setFormError("Pilih karyawan penerima.");
    if (conflict) return setFormError(`Aset dipakai ${row?.used_by_team_name ?? "tim lain"} pada tanggal ini.`);
    const photo = (e.currentTarget.elements.namedItem("handover_photo") as HTMLInputElement | null)?.files?.[0];
    try {
      let handover_file_id: string | null = null;
      if (photo) {
        const body = new FormData();
        body.set("file", photo);
        handover_file_id = (await upload.mutateAsync(body)).file_id;
      }
      await lend.mutateAsync({
        asset_type: kind,
        ...(kind === "TOOL" ? { tool_id: assetId } : { vehicle_id: assetId }),
        employee_id: employeeId,
        handover_file_id,
        ...(dailyPlanId ? { daily_plan_id: dailyPlanId } : {}),
      });
      toast.success(`${assetName} diserahkan.`);
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  };

  return (
    <AssetFormDialog title={`Serahkan ${assetName}`} submitLabel="Serahkan" submitting={busy}
      submitDisabled={conflict} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      {kind === "VEHICLE" && (
        <TextBlock className="mb-3 text-sm text-mist">STNK harus berlaku (KIR untuk truk) dan pemegang wajib punya SIM yang sesuai.</TextBlock>
      )}
      <TextField label="Tanggal jadwal" type="date" value={workDate} onChange={(e) => { setWorkDate(e.target.value); setDailyPlanId(""); }} />
      <SelectField label="Tim pemakai (opsional)" value={teamId} onChange={(e) => { setTeamId(e.target.value); setDailyPlanId(""); }}>
        <ControlOption value="">Tanpa tim</ControlOption>
        {teams.data?.map((t) => (
          <ControlOption key={t.team_id} value={t.team_id}>{t.name}</ControlOption>
        ))}
      </SelectField>
      <SelectField label="Jadwal harian (opsional)" value={dailyPlanId} onChange={(e) => {
        const id = e.target.value;
        setDailyPlanId(id);
        const plan = planOptions.find((p) => p.daily_plan_id === id);
        if (plan) setTeamId(plan.team_id);
      }}>
        <ControlOption value="">Tanpa jadwal</ControlOption>
        {planOptions.map((p) => (
          <ControlOption key={p.daily_plan_id} value={p.daily_plan_id}>
            {p.team_name} · {p.project_title ?? p.division_name}
          </ControlOption>
        ))}
      </SelectField>
      {conflict && (
        <TextBlock role="alert" className="mb-3 text-sm text-danger">
          Bentrok: aset ini dipakai {row?.used_by_team_name ?? "tim lain"} pada {workDate}. Pilih tanggal lain atau kembalikan dulu.
        </TextBlock>
      )}
      <TextField label="Cari karyawan" value={q} onChange={(e) => setQ(e.target.value)} hint="Nama, NIK, atau email" />
      <SelectField label="Karyawan penerima" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
        <ControlOption value="">Pilih karyawan</ControlOption>
        {employees.data?.items.map((emp) => (
          <ControlOption key={emp.employee_id} value={emp.employee_id}>
            {emp.full_name} · {emp.employee_no}
          </ControlOption>
        ))}
      </SelectField>
      <TextField name="handover_photo" label="Foto serah terima (opsional)" type="file" accept=".jpg,.jpeg,.png" />
    </AssetFormDialog>
  );
}
