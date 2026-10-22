import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { DialogActions } from "@/components/molecules/DialogActions";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import {
  geoSearch,
  useCreateDailyPlan,
  useUpdateDailyPlan,
  type DailyFormOptions,
  type DailyPlan,
  type GeoResult,
} from "@/services/dailyPlanService";

type Errors = Record<string, string>;

/** Buat/ubah jadwal harian: tim & tanggal, lokasi site (cari di peta), radius absen, jam kerja. */
export function DailyPlanFormDialog({ options, initial, plan, onClose }: {
  options: DailyFormOptions;
  /** Prefill dari sel matriks (tim & tanggal) saat membuat. */
  initial?: { team_id: string; work_date: string };
  /** Jadwal yang diubah (DRAFT/SUBMITTED). */
  plan?: DailyPlan;
  onClose: () => void;
}) {
  const create = useCreateDailyPlan();
  const update = useUpdateDailyPlan(plan?.daily_plan_id ?? "");
  const [teamId, setTeamId] = useState(plan?.team_id ?? initial?.team_id ?? "");
  const [siteName, setSiteName] = useState(plan?.site_name ?? "");
  const [lat, setLat] = useState(plan ? String(plan.site_lat) : "");
  const [lng, setLng] = useState(plan ? String(plan.site_lng) : "");
  const [hits, setHits] = useState<GeoResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const busy = create.isPending || update.isPending;

  const search = async () => {
    setFormError(null);
    setSearching(true);
    try {
      setHits((await geoSearch(siteName)).slice(0, 5));
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Pencarian lokasi gagal.");
    } finally {
      setSearching(false);
    }
  };

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const team = options.teams.find((t) => t.team_id === teamId);
    const value = (k: string) => String(f.get(k) ?? "").trim();
    setErrors({});
    setFormError(null);
    if (!team) return setErrors({ team_id: "Pilih tim." });
    if (siteName.trim().length < 2) return setErrors({ site_name: "Nama lokasi wajib diisi." });
    if (!lat || !lng || Number.isNaN(Number(lat)) || Number.isNaN(Number(lng))) return setErrors({ site_lat: "Isi koordinat atau pilih dari pencarian." });
    const body = {
      site_name: siteName.trim(),
      site_lat: lat,
      site_lng: lng,
      attendance_radius_m: Number(value("attendance_radius_m") || 150),
      clock_in_time: value("clock_in_time") || "07:00",
      clock_out_time: value("clock_out_time") || "16:00",
    };
    try {
      if (plan) {
        await update.mutateAsync({ ...body, team_id: team.team_id, work_date: value("work_date") || plan.work_date });
        toast.success("Jadwal diperbarui.");
      } else {
        await create.mutateAsync({ ...body, division_id: team.division_id, team_id: team.team_id, work_date: value("work_date") });
        toast.success("Jadwal dibuat sebagai draf.");
      }
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details.fields) setErrors(err.details.fields as Errors);
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };

  return (
    <VmsDialog open title={plan ? "Ubah jadwal harian" : "Buat jadwal harian"} onClose={onClose} footer={<DialogActions onCancel={onClose} busy={busy} formId="daily-plan-form" />}>
      <FormBlock id="daily-plan-form" onSubmit={submit} noValidate>
        <FormErrorText message={formError} />
        <SelectField label="Tim" value={teamId} onChange={(e) => setTeamId(e.target.value)} error={errors.team_id}>
          <ControlOption value="">Pilih tim</ControlOption>
          {options.teams.map((t) => (
            <ControlOption key={t.team_id} value={t.team_id}>
              {t.name} · ketua {t.leader_name}
            </ControlOption>
          ))}
        </SelectField>
        <TextField name="work_date" label="Tanggal" type="date" defaultValue={plan?.work_date ?? initial?.work_date} error={errors.work_date} />
        <TextField label="Lokasi site" value={siteName} onChange={(e) => setSiteName(e.target.value)} error={errors.site_name} hint="Nama site/titik kumpul tim (dipakai untuk absen)." />
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <ActionButton type="button" size="sm" variant="outline" disabled={searching || siteName.trim().length < 3} onClick={search}>
            {searching ? "Mencari…" : "Cari koordinat"}
          </ActionButton>
          {hits.map((h) => (
            <ActionButton
              key={`${h.lat},${h.lng}`}
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setLat(h.lat.toFixed(7));
                setLng(h.lng.toFixed(7));
                setHits([]);
              }}
            >
              {h.name.split(",").slice(0, 2).join(",")}
            </ActionButton>
          ))}
        </div>
        <div className="grid gap-x-3 md:grid-cols-2">
          <TextField label="Lintang (lat)" inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} error={errors.site_lat} />
          <TextField label="Bujur (lng)" inputMode="decimal" value={lng} onChange={(e) => setLng(e.target.value)} error={errors.site_lng} />
        </div>
        <div className="grid gap-x-3 md:grid-cols-3">
          <TextField name="attendance_radius_m" label="Radius absen (m)" inputMode="numeric" defaultValue={String(plan?.attendance_radius_m ?? 150)} error={errors.attendance_radius_m} />
          <TextField name="clock_in_time" label="Jam masuk" type="time" defaultValue={(plan?.clock_in_time ?? "07:00").slice(0, 5)} />
          <TextField name="clock_out_time" label="Jam pulang" type="time" defaultValue={(plan?.clock_out_time ?? "16:00").slice(0, 5)} error={errors.clock_out_time} />
        </div>
      </FormBlock>
    </VmsDialog>
  );
}
