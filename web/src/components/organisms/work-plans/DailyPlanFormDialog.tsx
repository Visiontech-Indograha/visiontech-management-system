import { useState } from "react";
import { toast } from "sonner";
import { ChoiceChips } from "@/components/molecules/ChoiceChips";
import { DialogActions } from "@/components/molecules/DialogActions";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { useDirtyForm } from "@/hooks/useDirtyForm";
import { ApiError } from "@/lib/apiClient";
import { SiteMapPicker } from "@/components/organisms/sites/SiteMapPicker";
import { DailyPlanAssetsPanel } from "@/components/organisms/work-plans/DailyPlanAssetsPanel";
import {
  addDays,
  BACKDATE_DAYS,
  useCreateDailyPlan,
  useRecentSites,
  useUpdateDailyPlan,
  wibDate,
  type DailyFormOptions,
  type DailyPlan,
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
  const [lat, setLat] = useState(plan ? String(plan.site_lat ?? "") : "");
  const [lng, setLng] = useState(plan ? String(plan.site_lng ?? "") : "");
  const [radius, setRadius] = useState(String(plan?.attendance_radius_m ?? 150));
  const [workDate, setWorkDate] = useState(plan?.work_date ?? initial?.work_date ?? "");
  // F10: jadwal tanggal lampau (<= BACKDATE_DAYS hari, hanya saat membuat) wajib beralasan; tercatat audit.
  const [backdateReason, setBackdateReason] = useState("");
  const today = wibDate();
  const backdated = !plan && !!workDate && workDate < today;
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const recent = useRecentSites(plan ? "" : teamId);   // hanya saat membuat jadwal baru
  const busy = create.isPending || update.isPending;

  // Titik untuk peta: hanya bila kedua koordinat valid; mengetik manual ikut menggeser penanda.
  const point: [number, number] | null =
    lat.trim() && lng.trim() && Number.isFinite(Number(lat)) && Number.isFinite(Number(lng))
      ? [Number(lat), Number(lng)]
      : null;
  const radiusNum = Number(radius);

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const team = options.teams.find((t) => t.team_id === teamId);
    const value = (k: string) => String(f.get(k) ?? "").trim();
    setErrors({});
    setFormError(null);
    if (!team) return setErrors({ team_id: "Pilih tim." });
    const latitude = lat.trim();
    const longitude = lng.trim();
    if (siteName.trim() && siteName.trim().length < 2) return setErrors({ site_name: "Nama lokasi minimal 2 karakter." });
    if (Boolean(latitude) !== Boolean(longitude)) {
      return setErrors({ site_lat: "Isi kedua koordinat atau kosongkan keduanya.", site_lng: "Isi kedua koordinat atau kosongkan keduanya." });
    }
    if (latitude && (
      !Number.isFinite(Number(latitude)) || Math.abs(Number(latitude)) > 90 ||
      !Number.isFinite(Number(longitude)) || Math.abs(Number(longitude)) > 180
    )) {
      return setErrors({ site_lat: "Koordinat tidak valid (latitude -90..90, longitude -180..180)." });
    }
    const body = {
      site_name: siteName.trim() || null,
      site_lat: latitude ? Number(latitude) : null,
      site_lng: longitude ? Number(longitude) : null,
      attendance_radius_m: Number(value("attendance_radius_m") || 150),
      clock_in_time: value("clock_in_time") || "07:00",
      clock_out_time: value("clock_out_time") || "16:00",
    };
    if (backdated && !backdateReason.trim()) return setErrors({ backdate_reason: "Isi alasan untuk tanggal lampau." });
    try {
      if (plan) {
        await update.mutateAsync({ ...body, team_id: team.team_id, work_date: value("work_date") || plan.work_date });
        toast.success("Jadwal diperbarui.");
      } else {
        await create.mutateAsync({
          ...body,
          kind: "WORK",
          division_id: team.division_id,
          team_id: team.team_id,
          work_date: value("work_date"),
          ...(backdated ? { backdate_reason: backdateReason.trim() } : {}),
        });
        toast.success(backdated ? "Jadwal tanggal lampau dibuat sebagai draf (tercatat)." : "Jadwal dibuat sebagai draf.");
      }
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details.fields) setErrors(err.details.fields as Errors);
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };

  const dirtyForm = useDirtyForm();
  return (
    <VmsDialog dirty={dirtyForm.dirty} open title={plan ? "Ubah jadwal harian" : "Buat jadwal harian"} onClose={onClose} footer={<DialogActions onCancel={onClose} busy={busy} formId="daily-plan-form" />}>
      <FormBlock {...dirtyForm.formProps} id="daily-plan-form" onSubmit={submit} noValidate>
        <FormErrorText message={formError} />
        <SelectField label="Tim" value={teamId} onChange={(e) => setTeamId(e.target.value)} error={errors.team_id}>
          <ControlOption value="">Pilih tim</ControlOption>
          {options.teams.map((t) => (
            <ControlOption key={t.team_id} value={t.team_id}>
              {t.name} · ketua {t.leader_name}
            </ControlOption>
          ))}
        </SelectField>
        <TextField
          name="work_date"
          label="Tanggal"
          type="date"
          value={workDate}
          min={plan ? today : addDays(today, -BACKDATE_DAYS)}
          onChange={(e) => setWorkDate(e.target.value)}
          error={errors.work_date}
        />
        {backdated && (
          <TextField
            name="backdate_reason"
            label={`Alasan tanggal lampau (maks. ${BACKDATE_DAYS} hari)`}
            value={backdateReason}
            onChange={(e) => setBackdateReason(e.target.value)}
            maxLength={300}
            error={errors.backdate_reason}
            hint="Dicatat di audit. Jadwal dibuat sebagai draf dan tetap perlu diajukan/disetujui."
          />
        )}
        <TextField label="Lokasi site (opsional)" value={siteName} onChange={(e) => setSiteName(e.target.value)} error={errors.site_name} hint="Jadwal dapat dibuat sebelum lokasi diketahui; koordinat wajib dilengkapi sebelum presensi." />
        <ChoiceChips
          label="Lokasi terakhir tim:"
          testId="recent-sites"
          items={(recent.data ?? []).map((s) => ({ key: `${s.site_name}|${s.site_lat}|${s.site_lng}`, label: s.site_name }))}
          onPick={(key) => {
            const s = recent.data?.find((x) => `${x.site_name}|${x.site_lat}|${x.site_lng}` === key);
            if (!s) return;
            setSiteName(s.site_name);
            setLat(String(s.site_lat));
            setLng(String(s.site_lng));
            if (s.attendance_radius_m) setRadius(String(s.attendance_radius_m));
          }}
        />
        <SiteMapPicker
          point={point}
          radius={Number.isFinite(radiusNum) && radiusNum > 0 ? radiusNum : null}
          onPick={(p, label) => {
            setLat(p[0].toFixed(7));
            setLng(p[1].toFixed(7));
            if (label && !siteName.trim()) setSiteName(label.split(",")[0]!.trim());
          }}
        />
        <div className="grid gap-x-3 md:grid-cols-2">
          <TextField label="Lintang (lat)" inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} error={errors.site_lat} />
          <TextField label="Bujur (lng)" inputMode="decimal" value={lng} onChange={(e) => setLng(e.target.value)} error={errors.site_lng} />
        </div>
        <DailyPlanAssetsPanel teamId={teamId} workDate={workDate} />
        <div className="grid gap-x-3 md:grid-cols-3">
          <TextField name="attendance_radius_m" label="Radius absen (m)" inputMode="numeric" value={radius} onChange={(e) => setRadius(e.target.value)} error={errors.attendance_radius_m} />
          <TextField name="clock_in_time" label="Jam masuk" type="time" defaultValue={(plan?.clock_in_time ?? "07:00").slice(0, 5)} />
          <TextField name="clock_out_time" label="Jam pulang" type="time" defaultValue={(plan?.clock_out_time ?? "16:00").slice(0, 5)} error={errors.clock_out_time} />
        </div>
      </FormBlock>
    </VmsDialog>
  );
}
