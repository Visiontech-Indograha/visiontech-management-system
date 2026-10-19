/**
 * web/src/components/organisms/work-plans/PlanEditorV2Form.tsx
 * Formulir Terintegrasi Pembuatan & Penyuntingan Rencana Kerja (Work Plan V2):
 * - Level Mingguan (work_plan_weekly): Divisi, Tim (Ketua & Teknisi), Minggu ke-N, Tahun, Rentang Tanggal
 * - Level Harian (work_plan_daily): Tanggal, Nama Site, Koordinat GPS, Radius Presensi, Jam Kerja, Hari Libur
 * - Level Butir Tugas (work_plan_item): Judul Tugas, Jenis Pekerjaan (terfilter divisi), Order Klien, Target Unit, Jam Slot, Lokasi Spesifik, Penugasan Teknisi
 * - Level Aset: Peralatan & Armada Operasional + Pengemudi
 */

import React, { useEffect, useMemo, useState } from "react";
import { useForm, useFieldArray, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  weeklyPlanV2Schema,
  type DailyPlanV2Value,
  type PlanItemV2Value,
  type WeeklyPlanV2Value,
} from "@/schemas/workPlanV2Schema";
import {
  useCreateWeeklyPlanV2,
  useUpdateWeeklyPlanV2,
  useWorkPlanFormOptionsV2,
  type WeeklyPlanDetailResponse,
} from "@/services/workPlanV2Service";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FormBlock, ControlLabel, ControlInput, ControlSelect, ControlOption } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { QueryState } from "@/components/molecules/QueryState";
import { CalendarClock, MapPin, Timer, Trash2 } from "@/components/molecules/Glyphs";
import { weekday } from "@/lib/weekday";
import { formatDate } from "@/lib/format";

/** Hitung tanggal Senin dan Minggu berdasarkan tahun dan nomor minggu ISO */
function getIsoWeekRange(year: number, week: number): { start: string; end: string } {
  const simple = new Date(Date.UTC(year, 0, 1 + (week - 1) * 7));
  const dow = simple.getUTCDay();
  const isoStart = new Date(simple);
  if (dow <= 4) {
    isoStart.setUTCDate(simple.getUTCDate() - simple.getUTCDay() + 1);
  } else {
    isoStart.setUTCDate(simple.getUTCDate() + 8 - simple.getUTCDay());
  }
  const isoEnd = new Date(isoStart);
  isoEnd.setUTCDate(isoStart.getUTCDate() + 6);
  return {
    start: isoStart.toISOString().slice(0, 10),
    end: isoEnd.toISOString().slice(0, 10),
  };
}

/** Hitung nomor minggu saat ini */
function getCurrentIsoWeek(): { year: number; week: number } {
  const now = new Date();
  const d = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return { year: d.getUTCFullYear(), week: weekNo };
}

/** Array tanggal ISO antara start dan end inklusif */
function getDatesInRange(start: string, end: string): string[] {
  if (!start || !end || end < start) return [];
  const out: string[] = [];
  const curr = new Date(`${start}T00:00:00Z`);
  const stop = new Date(`${end}T00:00:00Z`);
  while (curr <= stop && out.length < 31) {
    out.push(curr.toISOString().slice(0, 10));
    curr.setUTCDate(curr.getUTCDate() + 1);
  }
  return out;
}

interface PlanEditorV2FormProps {
  planId?: string;
  initialData?: WeeklyPlanDetailResponse;
}

export const PlanEditorV2Form: React.FC<PlanEditorV2FormProps> = ({ planId, initialData }) => {
  const navigate = useNavigate();
  const optionsQuery = useWorkPlanFormOptionsV2();
  const opts = optionsQuery.data;

  const currentIso = useMemo(() => getCurrentIsoWeek(), []);
  const defaultWeekRange = useMemo(
    () => getIsoWeekRange(currentIso.year, currentIso.week),
    [currentIso]
  );

  const {
    register,
    control,
    handleSubmit,
    setValue,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<WeeklyPlanV2Value>({
    resolver: zodResolver(weeklyPlanV2Schema),
    defaultValues: initialData ?? {
      division_id: "",
      team_id: "",
      week_number: currentIso.week,
      year: currentIso.year,
      start_date: defaultWeekRange.start,
      end_date: defaultWeekRange.end,
      status: "APPROVED",
      tool_ids: [],
      vehicle_id: "",
      driver_employee_id: "",
      days: [],
    },
  });

  const { fields: dayFields, replace: replaceDays } = useFieldArray({
    control,
    name: "days",
  });

  const selectedDivisionId = useWatch({ control, name: "division_id" });
  const selectedTeamId = useWatch({ control, name: "team_id" });
  const startDate = useWatch({ control, name: "start_date" });
  const endDate = useWatch({ control, name: "end_date" });
  const weekNum = useWatch({ control, name: "week_number" });
  const yearNum = useWatch({ control, name: "year" });

  const [formError, setFormError] = useState<string | null>(null);

  // Filter tim sesuai divisi terpilih
  const filteredTeams = useMemo(() => {
    if (!opts?.teams) return [];
    if (!selectedDivisionId) return opts.teams;
    return opts.teams.filter((t) => t.division_id === selectedDivisionId);
  }, [opts?.teams, selectedDivisionId]);

  // Tim yang sedang dipilih
  const activeTeam = useMemo(() => {
    if (!opts?.teams || !selectedTeamId) return null;
    return opts.teams.find((t) => t.team_id === selectedTeamId) || null;
  }, [opts?.teams, selectedTeamId]);

  // Filter work types sesuai divisi terpilih
  const filteredWorkTypes = useMemo(() => {
    if (!opts?.work_types) return [];
    if (!selectedDivisionId) return opts.work_types;
    return opts.work_types.filter((wt) => wt.division_id === selectedDivisionId);
  }, [opts?.work_types, selectedDivisionId]);

  // Filter completions sesuai divisi terpilih
  const filteredCompletions = useMemo(() => {
    if (!opts?.work_completions) return [];
    if (!selectedDivisionId) return opts.work_completions;
    return opts.work_completions.filter(
      (c) => !c.division_id || c.division_id === selectedDivisionId
    );
  }, [opts?.work_completions, selectedDivisionId]);

  // Calon teknisi (gabungan ketua dan anggota tim aktif)
  const availableTechnicians = useMemo(() => {
    if (!activeTeam) return [];
    const list = [...activeTeam.members];
    if (
      activeTeam.leader_employee_id &&
      !list.some((m) => m.employee_id === activeTeam.leader_employee_id)
    ) {
      list.unshift({
        employee_id: activeTeam.leader_employee_id,
        full_name: `${activeTeam.leader_name || "Ketua Tim"} (Ketua)`,
        position: activeTeam.leader_position || "Team Leader",
      });
    }
    return list;
  }, [activeTeam]);

  // Inisialisasi default divisi dan tim saat opsi selesai dimuat jika form baru
  useEffect(() => {
    if (!initialData && opts) {
      if (!getValues("division_id") && opts.divisions.length > 0) {
        setValue("division_id", opts.divisions[0].division_id);
      }
    }
  }, [opts, initialData, setValue, getValues]);

  // Auto-select tim pertama ketika divisi berubah jika tim sebelumnya tidak relevan
  useEffect(() => {
    if (selectedDivisionId && filteredTeams.length > 0) {
      const curTeam = getValues("team_id");
      if (!curTeam || !filteredTeams.some((t) => t.team_id === curTeam)) {
        setValue("team_id", filteredTeams[0].team_id);
      }
    }
  }, [selectedDivisionId, filteredTeams, setValue, getValues]);

  // Perubahan minggu/tahun -> auto update start_date dan end_date jika belum diedit manual
  const handleWeekChange = (w: number, y: number) => {
    setValue("week_number", w);
    setValue("year", y);
    const range = getIsoWeekRange(y, w);
    setValue("start_date", range.start);
    setValue("end_date", range.end);
  };

  // Sinkronisasi hari-hari kerja saat start_date atau end_date berubah
  useEffect(() => {
    if (!startDate || !endDate || endDate < startDate) return;
    const targetDates = getDatesInRange(startDate, endDate);
    const existingDays = getValues("days") || [];
    const existingMap = new Map(existingDays.map((d) => [d.work_date, d]));

    const defaultOffice = opts?.offices?.[0];
    const defaultSiteName = defaultOffice?.name || "Site Proyek";
    const defaultLat = defaultOffice?.latitude || 3.5952;
    const defaultLng = defaultOffice?.longitude || 98.6722;
    const defaultRadius = defaultOffice?.radius_m || 150;

    const newDays: DailyPlanV2Value[] = targetDates.map((dateStr) => {
      const existing = existingMap.get(dateStr);
      if (existing) return existing;

      // Default item slot untuk hari baru
      const defaultItem: PlanItemV2Value = {
        title: "Pekerjaan Lapangan",
        work_type_id: filteredWorkTypes[0]?.work_type_id || "",
        task_phase: "MAIN_INSTALLATION",
        is_main_deliverable: true,
        target_qty: 1,
        completed_qty: 0,
        progress_percent: 0,
        start_time: "08:00:00",
        end_time: "17:00:00",
        status: "PENDING",
        rollover_approval_status: "NONE",
        assigned_employee_ids: activeTeam?.leader_employee_id ? [activeTeam.leader_employee_id] : [],
      };

      return {
        work_date: dateStr,
        site_name: defaultSiteName,
        site_lat: defaultLat,
        site_lng: defaultLng,
        attendance_radius_m: defaultRadius,
        clock_in_time: "08:00:00",
        clock_out_time: "17:00:00",
        status: "SCHEDULED",
        is_holiday: false,
        items: [defaultItem],
      };
    });

    if (
      existingDays.length !== newDays.length ||
      existingDays.some((d, idx) => d.work_date !== newDays[idx]?.work_date)
    ) {
      replaceDays(newDays);
    }
  }, [startDate, endDate, filteredWorkTypes, activeTeam, opts?.offices, replaceDays, getValues]);

  // Gandakan setting hari pertama ke semua hari berikutnya
  const copyFirstDayToAll = () => {
    const current = getValues("days");
    if (!current || current.length <= 1) return;
    const first = current[0];

    const updated = current.map((day, idx) => {
      if (idx === 0) return day;
      return {
        ...day,
        site_name: first.site_name,
        site_lat: first.site_lat,
        site_lng: first.site_lng,
        attendance_radius_m: first.attendance_radius_m,
        clock_in_time: first.clock_in_time,
        clock_out_time: first.clock_out_time,
        items: first.items.map((it) => ({
          ...it,
          item_id: undefined,
          completed_qty: 0,
          progress_percent: 0,
          status: "PENDING" as const,
        })),
      };
    });

    replaceDays(updated);
    toast.success("Pengaturan lokasi, jam, dan slot tugas hari pertama disalin ke seluruh hari!");
  };

  const createMut = useCreateWeeklyPlanV2();
  const updateMut = useUpdateWeeklyPlanV2(planId ?? "");
  const isPending = createMut.isPending || updateMut.isPending || isSubmitting;

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      if (planId) {
        await updateMut.mutateAsync(values);
        toast.success("Rencana kerja mingguan berhasil diperbarui!");
        navigate(`/work-plans/${planId}`);
      } else {
        const created = await createMut.mutateAsync(values);
        toast.success("Rencana kerja mingguan baru berhasil diterbitkan!");
        const newId = created.weekly_plan_id || (created as unknown as { id: string }).id;
        navigate(newId ? `/work-plans/${newId}` : "/work-plans");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal menyimpan rencana kerja.";
      setFormError(msg);
      toast.error(msg);
    }
  });

  return (
    <QueryState query={optionsQuery} errorText="Gagal memuat opsi form master rencana kerja.">
      <form onSubmit={onSubmit} className="space-y-8">
        <FormErrorText message={formError} />

        {/* ── BAGIAN 1: HEADER MINGGUAN & TIM ──────────────────────── */}
        <section aria-label="Informasi Rencana Kerja Mingguan" className="rounded-panel border border-line bg-surface p-6 shadow-card">
          <div className="flex items-center gap-2 border-b border-line pb-4">
            <CalendarClock className="h-5 w-5 text-primary" />
            <TextBlock as="h2" className="text-lg font-semibold">
              1. Identitas &amp; Tim Kerja (Weekly Plan)
            </TextBlock>
          </div>

          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <FormBlock>
              <ControlLabel htmlFor="division_id">Divisi Operasional</ControlLabel>
              <ControlSelect
                id="division_id"
                {...register("division_id")}
                aria-invalid={!!errors.division_id}
              >
                <ControlOption value="">-- Pilih Divisi --</ControlOption>
                {opts?.divisions.map((d) => (
                  <ControlOption key={d.division_id} value={d.division_id}>
                    {d.name}
                  </ControlOption>
                ))}
              </ControlSelect>
              {errors.division_id && <FormErrorText message={errors.division_id.message} />}
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor="team_id">Tim Kerja Pelaksana</ControlLabel>
              <ControlSelect
                id="team_id"
                {...register("team_id")}
                aria-invalid={!!errors.team_id}
              >
                <ControlOption value="">-- Pilih Tim --</ControlOption>
                {filteredTeams.map((t) => (
                  <ControlOption key={t.team_id} value={t.team_id}>
                    {t.name}
                  </ControlOption>
                ))}
              </ControlSelect>
              {errors.team_id && <FormErrorText message={errors.team_id.message} />}
            </FormBlock>
          </div>

          {/* Banner Tim Terpilih */}
          {activeTeam && (
            <div className="mt-4 rounded-panel border border-primary/20 bg-primary/5 p-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <TextBlock className="text-xs font-semibold uppercase tracking-wider text-primary">
                    Struktur Tim Lapangan
                  </TextBlock>
                  <TextBlock className="font-semibold text-ink">
                    Ketua Tim: {activeTeam.leader_name || "Belum ditentukan"} ({activeTeam.leader_position || "Team Leader"})
                  </TextBlock>
                </div>
                <div className="text-xs text-mist">
                  {activeTeam.members.length} Teknisi Lapangan Terdaftar
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {activeTeam.members.map((m) => (
                  <span
                    key={m.employee_id}
                    className="inline-flex items-center rounded-md border border-line bg-surface px-2.5 py-1 text-xs font-medium text-ink shadow-sm"
                  >
                    👤 {m.full_name} <span className="ml-1 text-[10px] text-mist">({m.position})</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <FormBlock>
              <ControlLabel htmlFor="year">Tahun</ControlLabel>
              <ControlInput
                id="year"
                type="number"
                min={2020}
                max={2100}
                {...register("year", { valueAsNumber: true })}
                onChange={(e) => handleWeekChange(weekNum, parseInt(e.target.value, 10) || currentIso.year)}
              />
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor="week_number">Minggu Ke-</ControlLabel>
              <ControlInput
                id="week_number"
                type="number"
                min={1}
                max={53}
                {...register("week_number", { valueAsNumber: true })}
                onChange={(e) => handleWeekChange(parseInt(e.target.value, 10) || 1, yearNum)}
              />
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor="start_date">Tanggal Mulai (Senin)</ControlLabel>
              <ControlInput id="start_date" type="date" {...register("start_date")} />
              {errors.start_date && <FormErrorText message={errors.start_date.message} />}
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor="end_date">Tanggal Selesai (Minggu/Sabtu)</ControlLabel>
              <ControlInput id="end_date" type="date" {...register("end_date")} />
              {errors.end_date && <FormErrorText message={errors.end_date.message} />}
            </FormBlock>
          </div>
        </section>

        {/* ── BAGIAN 2: JADWAL HARIAN & MULTI-SLOT TUGAS ───────────── */}
        <section aria-label="Rincian Hari & Butir Tugas" className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-primary" />
              <TextBlock as="h2" className="text-lg font-semibold">
                2. Breakdown Jadwal Harian &amp; Multi-Slot Tugas
              </TextBlock>
            </div>
            {dayFields.length > 1 && (
              <ActionButton
                type="button"
                variant="outline"
                onClick={copyFirstDayToAll}
                className="text-xs"
              >
                Samakan Pengaturan Hari ke Semua
              </ActionButton>
            )}
          </div>

          <div className="space-y-6">
            {dayFields.map((dayField, dayIndex) => (
              <DailyPlanCardItem
                key={dayField.id}
                dayIndex={dayIndex}
                control={control}
                register={register}
                setValue={setValue}
                offices={opts?.offices || []}
                workTypes={filteredWorkTypes}
                completions={filteredCompletions}
                technicians={availableTechnicians}
              />
            ))}
          </div>
        </section>

        {/* ── BAGIAN 3: ALAT & ARMADA KENDARAAN ────────────────────── */}
        <section aria-label="Alat & Kendaraan" className="rounded-panel border border-line bg-surface p-6 shadow-card">
          <div className="flex items-center gap-2 border-b border-line pb-4">
            <span className="text-xl">🔧</span>
            <TextBlock as="h2" className="text-lg font-semibold">
              3. Alokasi Peralatan Kerja &amp; Armada Kendaraan
            </TextBlock>
          </div>

          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <FormBlock>
              <ControlLabel htmlFor="vehicle_id">Armada Operasional (Kendaraan)</ControlLabel>
              <ControlSelect id="vehicle_id" {...register("vehicle_id")}>
                <ControlOption value="">-- Tanpa Kendaraan Operasional --</ControlOption>
                {opts?.vehicles.map((v) => (
                  <ControlOption key={v.vehicle_id} value={v.vehicle_id}>
                    [{v.vehicle_type}] {v.name} ({v.number_plate})
                  </ControlOption>
                ))}
              </ControlSelect>
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor="driver_employee_id">Pengemudi / Driver Ditunjuk</ControlLabel>
              <ControlSelect id="driver_employee_id" {...register("driver_employee_id")}>
                <ControlOption value="">-- Pilih Anggota Tim sebagai Driver --</ControlOption>
                {availableTechnicians.map((t) => (
                  <ControlOption key={t.employee_id} value={t.employee_id}>
                    {t.full_name}
                  </ControlOption>
                ))}
              </ControlSelect>
            </FormBlock>
          </div>

          {opts?.tools && opts.tools.length > 0 && (
            <div className="mt-6 border-t border-line pt-4">
              <ControlLabel>Peralatan yang Dialokasikan (Pilih yang relevan)</ControlLabel>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
                {opts.tools.map((tool) => {
                  return (
                    <label
                      key={tool.tool_id}
                      className="flex cursor-pointer items-center gap-2 rounded-md border border-line p-2 text-xs hover:bg-canvas"
                    >
                      <input
                        type="checkbox"
                        value={tool.tool_id}
                        {...register("tool_ids")}
                        className="rounded border-line text-primary focus:ring-primary"
                      />
                      <span className="truncate font-medium">{tool.name}</span>
                      <span className="text-[10px] text-mist">({tool.tool_code})</span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        {/* ── TOMBOL AKSI SIMPAN ───────────────────────────────────── */}
        <div className="flex items-center justify-end gap-3 border-t border-line pt-6">
          <ActionButton
            type="button"
            variant="outline"
            onClick={() => navigate("/work-plans")}
            disabled={isPending}
          >
            Batal
          </ActionButton>
          <ActionButton type="submit" variant="default" disabled={isPending}>
            {isPending
              ? "Menyimpan Data..."
              : planId
              ? "Perbarui Rencana Kerja"
              : "Terbitkan Rencana Kerja Mingguan"}
          </ActionButton>
        </div>
      </form>
    </QueryState>
  );
};

// ── SUB-KOMPONEN KARTU HARI KERJA & MULTI-SLOT TUGAS ─────────

interface DailyPlanCardItemProps {
  dayIndex: number;
  control: any;
  register: any;
  setValue: any;
  offices: any[];
  workTypes: any[];
  completions: any[];
  technicians: any[];
}

const DailyPlanCardItem: React.FC<DailyPlanCardItemProps> = ({
  dayIndex,
  control,
  register,
  setValue,
  offices,
  workTypes,
  completions,
  technicians,
}) => {
  const dayValue = useWatch({ control, name: `days.${dayIndex}` });
  const isHoliday = dayValue?.is_holiday || dayValue?.status === "HOLIDAY";

  const {
    fields: itemFields,
    append: appendItem,
    remove: removeItem,
  } = useFieldArray({
    control,
    name: `days.${dayIndex}.items`,
  });

  const handleSelectOffice = (officeId: string) => {
    const found = offices.find((o) => o.office_id === officeId);
    if (found) {
      setValue(`days.${dayIndex}.site_name`, found.name);
      setValue(`days.${dayIndex}.site_lat`, found.latitude);
      setValue(`days.${dayIndex}.site_lng`, found.longitude);
      if (found.radius_m) {
        setValue(`days.${dayIndex}.attendance_radius_m`, found.radius_m);
      }
    }
  };

  const toggleHoliday = () => {
    const next = !isHoliday;
    setValue(`days.${dayIndex}.is_holiday`, next);
    setValue(`days.${dayIndex}.status`, next ? "HOLIDAY" : "SCHEDULED");
  };

  const addItemSlot = () => {
    appendItem({
      title: "",
      work_type_id: workTypes[0]?.work_type_id || "",
      task_phase: "MAIN_INSTALLATION",
      is_main_deliverable: true,
      completion_id: null,
      target_qty: 1,
      completed_qty: 0,
      progress_percent: 0,
      start_time: "08:00:00",
      end_time: "12:00:00",
      location_name: "",
      status: "PENDING",
      rollover_approval_status: "NONE",
      assigned_employee_ids: technicians.length > 0 ? [technicians[0].employee_id] : [],
    });
  };

  return (
    <div
      className={`rounded-panel border p-5 shadow-card transition-all ${
        isHoliday
          ? "border-amber-200 bg-amber-50/40 dark:border-amber-900/40 dark:bg-amber-950/20"
          : "border-line bg-surface"
      }`}
    >
      {/* Header Baris Hari */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-canvas px-3 py-1.5 text-center border border-line">
            <span className="block text-xs font-semibold uppercase text-primary">
              {dayValue?.work_date ? weekday(dayValue.work_date) : "Hari"}
            </span>
            <span className="block text-sm font-bold text-ink">
              {dayValue?.work_date ? formatDate(dayValue.work_date) : "-"}
            </span>
          </div>

          <div>
            <TextBlock className="font-semibold text-ink">
              {dayValue?.site_name || "Lokasi Belum Ditentukan"}
            </TextBlock>
            <TextBlock className="text-xs text-mist">
              Radius Presensi: {dayValue?.attendance_radius_m || 150} meter • Jam:{" "}
              {dayValue?.clock_in_time?.slice(0, 5) || "08:00"} -{" "}
              {dayValue?.clock_out_time?.slice(0, 5) || "17:00"}
            </TextBlock>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ActionButton
            type="button"
            variant="outline"
            onClick={toggleHoliday}
            className={`text-xs ${isHoliday ? "border-amber-500 bg-amber-100 text-amber-800" : ""}`}
          >
            {isHoliday ? "✓ Ditandai Hari Libur" : "Set Hari Libur"}
          </ActionButton>
        </div>
      </div>

      {!isHoliday && (
        <div className="mt-4 space-y-4">
          {/* Baris Pengaturan Lokasi & Jam Kerja Harian */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <FormBlock>
              <ControlLabel htmlFor={`days_${dayIndex}_preset`}>Preset Lokasi Kantor/Site</ControlLabel>
              <ControlSelect
                id={`days_${dayIndex}_preset`}
                defaultValue=""
                onChange={(e) => handleSelectOffice(e.target.value)}
              >
                <ControlOption value="">-- Pilih preset --</ControlOption>
                {offices.map((o) => (
                  <ControlOption key={o.office_id} value={o.office_id}>
                    {o.name}
                  </ControlOption>
                ))}
              </ControlSelect>
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor={`days_${dayIndex}_site`}>Nama Site / Area Proyek</ControlLabel>
              <ControlInput
                id={`days_${dayIndex}_site`}
                type="text"
                placeholder="Site STO Telkom..."
                {...register(`days.${dayIndex}.site_name`)}
                required
              />
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor={`days_${dayIndex}_clock_in`}>Jam Masuk</ControlLabel>
              <ControlInput
                id={`days_${dayIndex}_clock_in`}
                type="time"
                {...register(`days.${dayIndex}.clock_in_time`)}
              />
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor={`days_${dayIndex}_clock_out`}>Jam Pulang</ControlLabel>
              <ControlInput
                id={`days_${dayIndex}_clock_out`}
                type="time"
                {...register(`days.${dayIndex}.clock_out_time`)}
              />
            </FormBlock>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <FormBlock>
              <ControlLabel htmlFor={`days_${dayIndex}_lat`}>Latitude GPS</ControlLabel>
              <ControlInput
                id={`days_${dayIndex}_lat`}
                type="number"
                step="any"
                {...register(`days.${dayIndex}.site_lat`, { valueAsNumber: true })}
              />
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor={`days_${dayIndex}_lng`}>Longitude GPS</ControlLabel>
              <ControlInput
                id={`days_${dayIndex}_lng`}
                type="number"
                step="any"
                {...register(`days.${dayIndex}.site_lng`, { valueAsNumber: true })}
              />
            </FormBlock>

            <FormBlock>
              <ControlLabel htmlFor={`days_${dayIndex}_radius`}>Radius Presensi (Meter)</ControlLabel>
              <ControlInput
                id={`days_${dayIndex}_radius`}
                type="number"
                min={10}
                {...register(`days.${dayIndex}.attendance_radius_m`, { valueAsNumber: true })}
              />
            </FormBlock>
          </div>

          {/* Sub-Section: Multi-Slot Butir Tugas */}
          <div className="mt-4 rounded-panel border border-line bg-canvas p-4">
            <div className="flex items-center justify-between border-b border-line pb-2">
              <div className="flex items-center gap-2">
                <Timer className="h-4 w-4 text-primary" />
                <TextBlock className="text-sm font-semibold text-ink">
                  Butir Tugas / Slot Kerja ({itemFields.length} Tugas)
                </TextBlock>
              </div>
              <ActionButton
                type="button"
                variant="outline"
                onClick={addItemSlot}
                className="text-xs font-medium"
              >
                + Tambah Slot Tugas
              </ActionButton>
            </div>

            <div className="mt-3 space-y-3">
              {itemFields.map((itemField, itemIndex) => (
                <ItemSlotRow
                  key={itemField.id}
                  dayIndex={dayIndex}
                  itemIndex={itemIndex}
                  control={control}
                  register={register}
                  setValue={setValue}
                  workTypes={workTypes}
                  completions={completions}
                  technicians={technicians}
                  onRemove={() => removeItem(itemIndex)}
                />
              ))}

              {itemFields.length === 0 && (
                <div className="py-4 text-center text-xs text-mist">
                  Belum ada slot tugas di hari ini. Klik &quot;+ Tambah Slot Tugas&quot; di atas.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── BARIS ITEM SLOT TUGAS ───────────────────────────────────

interface ItemSlotRowProps {
  dayIndex: number;
  itemIndex: number;
  control: any;
  register: any;
  setValue: any;
  workTypes: any[];
  completions: any[];
  technicians: any[];
  onRemove: () => void;
}

const ItemSlotRow: React.FC<ItemSlotRowProps> = ({
  dayIndex,
  itemIndex,
  control,
  register,
  setValue,
  workTypes,
  completions,
  technicians,
  onRemove,
}) => {
  const currentAssigned = useWatch({
    control,
    name: `days.${dayIndex}.items.${itemIndex}.assigned_employee_ids`,
  }) || [];

  const toggleTech = (empId: string) => {
    const next = currentAssigned.includes(empId)
      ? currentAssigned.filter((id: string) => id !== empId)
      : [...currentAssigned, empId];
    setValue(`days.${dayIndex}.items.${itemIndex}.assigned_employee_ids`, next);
  };

  return (
    <div className="rounded-md border border-line bg-surface p-3 shadow-sm transition-colors hover:border-primary/40">
      <div className="flex flex-col gap-3">
        {/* Baris 1: Judul Tugas, Jenis Pekerjaan, dan Target Qty */}
        <div className="grid gap-2 sm:grid-cols-12">
          <div className="sm:col-span-5">
            <ControlLabel className="text-xs">Judul Tugas / Aktivitas</ControlLabel>
            <ControlInput
              type="text"
              placeholder="Contoh: Penarikan Drop Core 12 Core Sektor Timur"
              {...register(`days.${dayIndex}.items.${itemIndex}.title`)}
              className="text-xs"
              required
            />
          </div>

          <div className="sm:col-span-4">
            <ControlLabel className="text-xs">Jenis Pekerjaan (Work Type)</ControlLabel>
            <ControlSelect
              {...register(`days.${dayIndex}.items.${itemIndex}.work_type_id`)}
              className="text-xs"
              required
            >
              {workTypes.map((wt) => (
                <ControlOption key={wt.work_type_id} value={wt.work_type_id}>
                  {wt.name}
                </ControlOption>
              ))}
            </ControlSelect>
          </div>

          <div className="sm:col-span-2">
            <ControlLabel className="text-xs">Target Qty</ControlLabel>
            <ControlInput
              type="number"
              step="any"
              min="0.01"
              {...register(`days.${dayIndex}.items.${itemIndex}.target_qty`, { valueAsNumber: true })}
              className="text-xs"
              required
            />
          </div>

          <div className="flex items-end justify-center sm:col-span-1">
            <button
              type="button"
              onClick={onRemove}
              className="rounded p-1.5 text-mist hover:bg-red-50 hover:text-red-600 transition-colors"
              title="Hapus slot tugas ini"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Baris 2: Order Klien (opsional), Jam Slot, dan Lokasi Spesifik */}
        <div className="grid gap-2 sm:grid-cols-12 text-xs">
          <div className="sm:col-span-4">
            <ControlLabel className="text-xs">Kaitan Order Klien (Opsional)</ControlLabel>
            <ControlSelect
              {...register(`days.${dayIndex}.items.${itemIndex}.completion_id`)}
              className="text-xs"
            >
              <ControlOption value="">-- Tanpa Order Spesifik --</ControlOption>
              {completions.map((c) => (
                <ControlOption key={c.completion_id} value={c.completion_id}>
                  [{c.client_name}] {c.project_title}
                </ControlOption>
              ))}
            </ControlSelect>
          </div>

          <div className="sm:col-span-2">
            <ControlLabel className="text-xs">Jam Mulai</ControlLabel>
            <ControlInput
              type="time"
              {...register(`days.${dayIndex}.items.${itemIndex}.start_time`)}
              className="text-xs"
            />
          </div>

          <div className="sm:col-span-2">
            <ControlLabel className="text-xs">Jam Selesai</ControlLabel>
            <ControlInput
              type="time"
              {...register(`days.${dayIndex}.items.${itemIndex}.end_time`)}
              className="text-xs"
            />
          </div>

          <div className="sm:col-span-4">
            <ControlLabel className="text-xs">Titik / Posisi Tiang (Opsional)</ControlLabel>
            <ControlInput
              type="text"
              placeholder="ODP-MDN-01 s/d 04"
              {...register(`days.${dayIndex}.items.${itemIndex}.location_name`)}
              className="text-xs"
            />
          </div>
        </div>

        {/* Baris 3: Teknisi yang ditugaskan */}
        {technicians.length > 0 && (
          <div className="mt-1 border-t border-line/60 pt-2">
            <span className="text-[11px] font-medium text-mist">Teknisi Bertugas di Slot Ini: </span>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {technicians.map((t) => {
                const isSelected = currentAssigned.includes(t.employee_id);
                return (
                  <button
                    key={t.employee_id}
                    type="button"
                    onClick={() => toggleTech(t.employee_id)}
                    className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium transition-colors ${
                      isSelected
                        ? "border-primary bg-primary/10 text-primary font-semibold"
                        : "border-line bg-canvas text-mist hover:text-ink"
                    }`}
                  >
                    <span>{isSelected ? "✓" : "+"}</span>
                    <span>{t.full_name}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
