/**
 * web/src/components/organisms/work-plans/PlanEditorV2Form.tsx
 * Formulir Rencana Kerja V2 Modern, Ringkas, dan Bersahabat (Daily-First Architecture):
 * - Stepper 3 Langkah Terarah: (1) Identitas & Tim -> (2) Jadwal Harian & Tugas -> (3) Armada & Alat (Opsional)
 * - Pemilih Hari Tab Horizontal: Hanya menampilkan 1 hari aktif agar pengguna tidak pusing/terintimidasi
 * - Fitur Cerdas Salin Hari: Cukup 1 klik untuk menyalin jadwal & tugas ke hari-hari kerja berikutnya
 * - GPS & Radius Opsional: Nilai default koordinat tersimpan otomatis tanpa harus diketik manual
 * - Manajemen Slot Tugas Ramah: Judul tugas, jenis pekerjaan, target unit, dan chip penugasan teknisi yang mudah diklik
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  useForm,
  useFieldArray,
  useWatch,
  type Control,
  type UseFormRegister,
  type UseFormSetValue,
} from "react-hook-form";
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
  type OfficeSiteOption,
  type TeamMemberOption,
  type WeeklyPlanDetailResponse,
  type WorkCompletionOption,
  type WorkTypeOption,
} from "@/services/workPlanV2Service";
import { ActionButton } from "@/components/molecules/ActionButton";
import { PlainAction } from "@/components/molecules/PlainAction";
import { TextBlock } from "@/components/molecules/TextBlock";
import { FormBlock, ControlLabel, ControlInput, ControlSelect, ControlOption } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { QueryState } from "@/components/molecules/QueryState";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import {
  ArrowLeft,
  ArrowRight,
  CalendarClock,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  MapPin,
  Plus,
  Sparkles,
  Timer,
  Trash2,
  User,
  Wrench,
} from "@/components/molecules/Glyphs";
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

  // Stepper: 1 = Info & Tim, 2 = Jadwal & Tugas, 3 = Armada & Alat
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  const [activeDayIndex, setActiveDayIndex] = useState<number>(0);
  const [isCopyModalOpen, setIsCopyModalOpen] = useState<boolean>(false);
  const [selectedTargetDates, setSelectedTargetDates] = useState<string[]>([]);

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
  const watchedDays = useWatch({ control, name: "days" }) || [];

  const [formError, setFormError] = useState<string | null>(null);

  // Filter tim sesuai divisi terpilih
  const filteredTeams = useMemo(() => {
    if (!opts?.teams) return [];
    if (!selectedDivisionId) return opts.teams;
    return opts.teams.filter((t) => t.division_id === selectedDivisionId);
  }, [opts, selectedDivisionId]);

  // Tim yang sedang dipilih
  const activeTeam = useMemo(() => {
    if (!opts?.teams || !selectedTeamId) return null;
    return opts.teams.find((t) => t.team_id === selectedTeamId) || null;
  }, [opts, selectedTeamId]);

  // Filter work types sesuai divisi terpilih
  const filteredWorkTypes = useMemo(() => {
    if (!opts?.work_types) return [];
    if (!selectedDivisionId) return opts.work_types;
    return opts.work_types.filter((wt) => wt.division_id === selectedDivisionId);
  }, [opts, selectedDivisionId]);

  // Filter completions sesuai divisi terpilih
  const filteredCompletions = useMemo(() => {
    if (!opts?.work_completions) return [];
    if (!selectedDivisionId) return opts.work_completions;
    return opts.work_completions.filter(
      (c) => !c.division_id || c.division_id === selectedDivisionId
    );
  }, [opts, selectedDivisionId]);

  // Calon teknisi (gabungan ketua dan anggota tim aktif)
  const availableTechnicians: TeamMemberOption[] = useMemo(() => {
    if (!activeTeam) return [];
    const list: TeamMemberOption[] = [...activeTeam.members];
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

  // Perubahan minggu/tahun -> auto update start_date dan end_date
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

    const newDays: DailyPlanV2Value[] = targetDates.map((dateStr, idx) => {
      const existing = existingMap.get(dateStr);
      if (existing) return existing;

      // Hari Sabtu (ke-6) dan Minggu (ke-7) default libur untuk kenyamanan
      const dObj = new Date(`${dateStr}T00:00:00Z`);
      const isWeekend = dObj.getUTCDay() === 0 || dObj.getUTCDay() === 6;

      // Default item slot untuk hari kerja baru
      const defaultItem: PlanItemV2Value = {
        title: `Pekerjaan Lapangan Hari ke-${idx + 1}`,
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
        status: isWeekend ? "HOLIDAY" : "SCHEDULED",
        is_holiday: isWeekend,
        items: isWeekend ? [] : [defaultItem],
      };
    });

    if (
      existingDays.length !== newDays.length ||
      existingDays.some((d, idx) => d.work_date !== newDays[idx]?.work_date)
    ) {
      replaceDays(newDays);
    }
  }, [startDate, endDate, filteredWorkTypes, activeTeam, opts?.offices, replaceDays, getValues]);

  // Buka modal salin jadwal hari aktif ke hari-hari lain
  const openCopyScheduleModal = () => {
    const current = getValues("days");
    if (!current || current.length <= 1) return;
    // Default centang semua hari selain hari aktif yang bukan hari libur
    const targets = current
      .filter((d, idx) => idx !== activeDayIndex && !d.is_holiday)
      .map((d) => d.work_date);
    setSelectedTargetDates(targets);
    setIsCopyModalOpen(true);
  };

  // Eksekusi penyalinan jadwal hari aktif ke target yang dipilih
  const executeCopySchedule = () => {
    const current = getValues("days");
    if (!current || activeDayIndex < 0 || activeDayIndex >= current.length) return;
    const sourceDay = current[activeDayIndex];
    if (!sourceDay) return;

    const targetSet = new Set(selectedTargetDates);
    const updated = current.map((day) => {
      if (!targetSet.has(day.work_date)) return day;
      return {
        ...day,
        site_name: sourceDay.site_name,
        site_lat: sourceDay.site_lat,
        site_lng: sourceDay.site_lng,
        attendance_radius_m: sourceDay.attendance_radius_m,
        clock_in_time: sourceDay.clock_in_time,
        clock_out_time: sourceDay.clock_out_time,
        status: "SCHEDULED" as const,
        is_holiday: false,
        items: sourceDay.items.map((it) => ({
          ...it,
          item_id: undefined,
          completed_qty: 0,
          progress_percent: 0,
          status: "PENDING" as const,
        })),
      };
    });

    replaceDays(updated);
    setIsCopyModalOpen(false);
    toast.success(`Jadwal & tugas berhasil disalin ke ${targetSet.size} hari terpilih!`);
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
      <FormBlock onSubmit={onSubmit} className="space-y-6">
        <FormErrorText message={formError} />

        {/* ── STEPPER NAVIGASI 3 LANGKAH ────────────────────────────── */}
        <nav aria-label="Tahapan formulir" className="grid grid-cols-3 gap-2 border-b border-line pb-4">
          <PlainAction
            type="button"
            onClick={() => setCurrentStep(1)}
            className={`flex items-center gap-2.5 p-3 rounded-panel border text-left transition-all ${
              currentStep === 1
                ? "border-primary bg-primary/10 text-primary font-semibold shadow-sm"
                : "border-line bg-surface text-mist hover:text-ink hover:bg-canvas"
            }`}
          >
            <div
              className={`size-7 rounded-full flex items-center justify-center text-xs font-bold ${
                currentStep === 1 ? "bg-primary text-white" : "bg-line text-mist"
              }`}
            >
              <TextBlock as="span">1</TextBlock>
            </div>
            <div>
              <TextBlock as="p" className="font-semibold text-xs sm:text-sm">Identitas &amp; Tim</TextBlock>
              <TextBlock as="p" className="text-[11px] text-mist hidden sm:block">Divisi, Tim &amp; Periode</TextBlock>
            </div>
          </PlainAction>

          <PlainAction
            type="button"
            onClick={() => setCurrentStep(2)}
            className={`flex items-center gap-2.5 p-3 rounded-panel border text-left transition-all ${
              currentStep === 2
                ? "border-primary bg-primary/10 text-primary font-semibold shadow-sm"
                : "border-line bg-surface text-mist hover:text-ink hover:bg-canvas"
            }`}
          >
            <div
              className={`size-7 rounded-full flex items-center justify-center text-xs font-bold ${
                currentStep === 2 ? "bg-primary text-white" : "bg-line text-mist"
              }`}
            >
              <TextBlock as="span">2</TextBlock>
            </div>
            <div>
              <TextBlock as="p" className="font-semibold text-xs sm:text-sm">Jadwal &amp; Tugas</TextBlock>
              <TextBlock as="p" className="text-[11px] text-mist hidden sm:block">Hari &amp; Slot Tugas</TextBlock>
            </div>
          </PlainAction>

          <PlainAction
            type="button"
            onClick={() => setCurrentStep(3)}
            className={`flex items-center gap-2.5 p-3 rounded-panel border text-left transition-all ${
              currentStep === 3
                ? "border-primary bg-primary/10 text-primary font-semibold shadow-sm"
                : "border-line bg-surface text-mist hover:text-ink hover:bg-canvas"
            }`}
          >
            <div
              className={`size-7 rounded-full flex items-center justify-center text-xs font-bold ${
                currentStep === 3 ? "bg-primary text-white" : "bg-line text-mist"
              }`}
            >
              <TextBlock as="span">3</TextBlock>
            </div>
            <div>
              <TextBlock as="p" className="font-semibold text-xs sm:text-sm">Armada &amp; Alat</TextBlock>
              <TextBlock as="p" className="text-[11px] text-mist hidden sm:block">Opsional</TextBlock>
            </div>
          </PlainAction>
        </nav>

        {/* ── LANGKAH 1: IDENTITAS & TIM ───────────────────────────── */}
        {currentStep === 1 && (
          <section aria-label="Identitas & Tim Kerja" className="rounded-panel border border-line bg-surface p-6 shadow-card space-y-6">
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div className="flex items-center gap-2">
                <CalendarClock className="h-5 w-5 text-primary" />
                <TextBlock as="h2" className="text-base font-semibold">
                  Langkah 1: Identitas &amp; Tim Pelaksana
                </TextBlock>
              </div>
              <TextBlock as="span" className="text-xs text-mist">Langkah 1 dari 3</TextBlock>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
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
              <div className="rounded-panel border border-primary/20 bg-primary/5 p-4 space-y-3">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <TextBlock className="text-xs font-semibold uppercase tracking-wider text-primary">
                      Tim Lapangan: {activeTeam.name}
                    </TextBlock>
                    <TextBlock className="font-semibold text-ink text-sm">
                      Ketua Tim: {activeTeam.leader_name || "Belum ditentukan"} ({activeTeam.leader_position || "Team Leader"})
                    </TextBlock>
                  </div>
                  <TextBlock as="p" className="text-xs text-mist">
                    {activeTeam.members.length} Teknisi Terdaftar
                  </TextBlock>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {activeTeam.members.map((m) => (
                    <TextBlock
                      as="span"
                      key={m.employee_id}
                      className="inline-flex items-center gap-1 rounded-md border border-line bg-surface px-2.5 py-1 text-xs font-medium text-ink shadow-sm"
                    >
                      <User className="h-3 w-3 text-mist" />
                      <TextBlock as="span">{m.full_name}</TextBlock>
                      <TextBlock as="span" className="text-[10px] text-mist">({m.position})</TextBlock>
                    </TextBlock>
                  ))}
                </div>
              </div>
            )}

            {/* Periode Kerja */}
            <div className="border-t border-line pt-4">
              <TextBlock className="text-xs font-semibold uppercase tracking-wider text-mist mb-3">
                Periode Pelaksanaan
              </TextBlock>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
                  <ControlLabel htmlFor="end_date">Tanggal Selesai (Minggu)</ControlLabel>
                  <ControlInput id="end_date" type="date" {...register("end_date")} />
                  {errors.end_date && <FormErrorText message={errors.end_date.message} />}
                </FormBlock>
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-line pt-4">
              <ActionButton
                type="button"
                variant="outline"
                onClick={() => navigate("/work-plans")}
              >
                Batal
              </ActionButton>
              <ActionButton
                type="button"
                variant="default"
                onClick={() => setCurrentStep(2)}
                className="gap-2"
              >
                <TextBlock as="span">Lanjut ke Jadwal Harian</TextBlock>
                <ArrowRight className="h-4 w-4" />
              </ActionButton>
            </div>
          </section>
        )}

        {/* ── LANGKAH 2: JADWAL & TUGAS HARIAN ──────────────────────── */}
        {currentStep === 2 && (
          <section aria-label="Jadwal & Tugas Harian" className="space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-line pb-3">
              <div>
                <TextBlock as="h2" className="text-base font-semibold flex items-center gap-2">
                  <MapPin className="h-5 w-5 text-primary" />
                  <TextBlock as="span">Langkah 2: Jadwal Harian &amp; Butir Tugas</TextBlock>
                </TextBlock>
                <TextBlock className="text-xs text-mist">
                  Pilih hari di bawah untuk mengatur lokasi dan tugas pada hari tersebut.
                </TextBlock>
              </div>
              <div className="flex items-center gap-2">
                {dayFields.length > 1 && (
                  <ActionButton
                    type="button"
                    variant="outline"
                    onClick={openCopyScheduleModal}
                    className="text-xs gap-1.5"
                  >
                    <Copy className="h-3.5 w-3.5 text-primary" />
                    <TextBlock as="span">Salin Jadwal Hari Ini ke Hari Lain</TextBlock>
                  </ActionButton>
                )}
              </div>
            </div>

            {/* TAB BAR PEMILIH HARI HORIZONTAL */}
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
              {dayFields.map((field, idx) => {
                const dayData = watchedDays[idx];
                const isActive = idx === activeDayIndex;
                const isHol = dayData?.is_holiday || dayData?.status === "HOLIDAY";
                const itemCount = dayData?.items?.length || 0;

                return (
                  <PlainAction
                    key={field.id}
                    type="button"
                    onClick={() => setActiveDayIndex(idx)}
                    className={`flex flex-col items-center justify-center min-w-[110px] px-3 py-2 rounded-panel border text-xs transition-all ${
                      isActive
                        ? "border-primary bg-primary text-white font-semibold shadow-sm"
                        : isHol
                        ? "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300"
                        : "border-line bg-surface text-ink hover:bg-canvas"
                    }`}
                  >
                    <TextBlock as="span" className="font-semibold text-xs">
                      {dayData?.work_date ? weekday(dayData.work_date) : `Hari ${idx + 1}`}
                    </TextBlock>
                    <TextBlock as="span" className="text-[11px] opacity-80 mt-0.5">
                      {dayData?.work_date ? formatDate(dayData.work_date).slice(0, 10) : "-"}
                    </TextBlock>
                    <TextBlock
                      as="span"
                      className={`mt-1.5 text-[10px] px-1.5 py-0.5 rounded-full ${
                        isActive
                          ? "bg-white/20 text-white font-medium"
                          : isHol
                          ? "bg-amber-200 text-amber-900 dark:bg-amber-900/60 dark:text-amber-200"
                          : "bg-canvas text-mist border border-line"
                      }`}
                    >
                      {isHol ? "Libur" : `${itemCount} Tugas`}
                    </TextBlock>
                  </PlainAction>
                );
              })}
            </div>

            {/* EDITOR SATU HARI AKTIF (SINGLE DAY FOCUS) */}
            {dayFields.length > 0 && activeDayIndex < dayFields.length && (
              <SingleDayPlanCard
                dayIndex={activeDayIndex}
                totalDays={dayFields.length}
                control={control}
                register={register}
                setValue={setValue}
                offices={opts?.offices || []}
                workTypes={filteredWorkTypes}
                completions={filteredCompletions}
                technicians={availableTechnicians}
                onPrevDay={() => setActiveDayIndex((prev) => Math.max(0, prev - 1))}
                onNextDay={() => setActiveDayIndex((prev) => Math.min(dayFields.length - 1, prev + 1))}
                onOpenCopyModal={openCopyScheduleModal}
              />
            )}

            {/* NAVIGASI LANGKAH 2 */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
              <ActionButton
                type="button"
                variant="outline"
                onClick={() => setCurrentStep(1)}
                className="gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                <TextBlock as="span">Kembali ke Tim</TextBlock>
              </ActionButton>

              <div className="flex items-center gap-3">
                <ActionButton
                  type="submit"
                  variant="outline"
                  disabled={isPending}
                  className="gap-1.5 border-primary/40 text-primary hover:bg-primary/5"
                >
                  <Sparkles className="h-4 w-4 text-primary" />
                  <TextBlock as="span">{isPending ? "Menyimpan..." : "Simpan Rencana Kerja"}</TextBlock>
                </ActionButton>
                <ActionButton
                  type="button"
                  variant="default"
                  onClick={() => setCurrentStep(3)}
                  className="gap-2"
                >
                  <TextBlock as="span">Lanjut ke Armada &amp; Alat</TextBlock>
                  <ArrowRight className="h-4 w-4" />
                </ActionButton>
              </div>
            </div>
          </section>
        )}

        {/* ── LANGKAH 3: ARMADA & ALAT (OPSIONAL) ───────────────────── */}
        {currentStep === 3 && (
          <section aria-label="Armada & Alat Kerja" className="rounded-panel border border-line bg-surface p-6 shadow-card space-y-6">
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div className="flex items-center gap-2">
                <Wrench className="h-5 w-5 text-primary" />
                <TextBlock as="h2" className="text-base font-semibold">
                  Langkah 3: Alokasi Armada Kendaraan &amp; Peralatan (Opsional)
                </TextBlock>
              </div>
              <TextBlock as="span" className="text-xs text-mist">Langkah 3 dari 3</TextBlock>
            </div>

            <TextBlock className="rounded-panel border border-line bg-canvas p-3 text-xs text-mist">
              💡 Bagian ini opsional. Jika tim tidak memerlukan kendaraan operasional atau alat khusus dari gudang, Anda dapat langsung menekan tombol &quot;Terbitkan Rencana Kerja&quot;.
            </TextBlock>

            <div className="grid gap-6 md:grid-cols-2">
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
              <div className="border-t border-line pt-4">
                <ControlLabel>Peralatan Kerja dari Gudang (Centang yang dibawa)</ControlLabel>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
                  {opts.tools.map((tool) => (
                    <ControlLabel
                      key={tool.tool_id}
                      className="flex cursor-pointer items-center gap-2 rounded-md border border-line p-2 text-xs hover:bg-canvas transition-colors"
                    >
                      <ControlInput
                        type="checkbox"
                        value={tool.tool_id}
                        {...register("tool_ids")}
                        className="rounded border-line text-primary focus:ring-primary size-4"
                      />
                      <TextBlock as="span" className="truncate font-medium">{tool.name}</TextBlock>
                      <TextBlock as="span" className="text-[10px] text-mist">({tool.tool_code})</TextBlock>
                    </ControlLabel>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between border-t border-line pt-6">
              <ActionButton
                type="button"
                variant="outline"
                onClick={() => setCurrentStep(2)}
                className="gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                <TextBlock as="span">Kembali ke Jadwal</TextBlock>
              </ActionButton>
              <ActionButton type="submit" variant="default" disabled={isPending} className="gap-2">
                <CheckCircle2 className="h-4 w-4" />
                <TextBlock as="span">
                  {isPending
                    ? "Menyimpan Data..."
                    : planId
                    ? "Perbarui Rencana Kerja"
                    : "Terbitkan Rencana Kerja Mingguan"}
                </TextBlock>
              </ActionButton>
            </div>
          </section>
        )}

        {/* ── MODAL SALIN JADWAL KE HARI LAIN ───────────────────────── */}
        <VmsDialog
          open={isCopyModalOpen}
          onClose={() => setIsCopyModalOpen(false)}
          title="Salin Jadwal & Tugas ke Hari Lain"
        >
          <div className="space-y-4 text-xs">
            <TextBlock className="text-mist">
              Lokasi, jam kerja, dan butir tugas dari hari{" "}
              <TextBlock as="strong" className="text-ink">
                {watchedDays[activeDayIndex]?.work_date
                  ? `${weekday(watchedDays[activeDayIndex].work_date)}, ${formatDate(
                      watchedDays[activeDayIndex].work_date
                    )}`
                  : `Hari ${activeDayIndex + 1}`}
              </TextBlock>{" "}
              akan disalin ke hari-hari terpilih di bawah ini:
            </TextBlock>

            <div className="flex gap-2">
              <ActionButton
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  const targets = watchedDays
                    .filter((d, idx) => idx !== activeDayIndex && !d.is_holiday)
                    .map((d) => d.work_date);
                  setSelectedTargetDates(targets);
                }}
              >
                Pilih Semua Hari Kerja
              </ActionButton>
              <ActionButton
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  const targets = watchedDays
                    .filter((_, idx) => idx !== activeDayIndex)
                    .map((d) => d.work_date);
                  setSelectedTargetDates(targets);
                }}
              >
                Pilih Seluruh Hari
              </ActionButton>
            </div>

            <div className="space-y-1.5 max-h-60 overflow-y-auto border border-line rounded-md p-2">
              {watchedDays.map((d, idx) => {
                if (idx === activeDayIndex) return null;
                const isSelected = selectedTargetDates.includes(d.work_date);
                return (
                  <ControlLabel
                    key={d.work_date}
                    className="flex items-center gap-2.5 p-2 rounded hover:bg-canvas cursor-pointer transition-colors"
                  >
                    <ControlInput
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedTargetDates((prev) => [...prev, d.work_date]);
                        } else {
                          setSelectedTargetDates((prev) => prev.filter((x) => x !== d.work_date));
                        }
                      }}
                      className="rounded border-line text-primary focus:ring-primary size-4"
                    />
                    <TextBlock as="span" className="font-semibold text-ink">{weekday(d.work_date)}</TextBlock>
                    <TextBlock as="span" className="text-mist">({formatDate(d.work_date)})</TextBlock>
                    {d.is_holiday && <TextBlock as="span" className="text-[10px] text-amber-600 font-medium">[Libur]</TextBlock>}
                  </ControlLabel>
                );
              })}
            </div>

            <div className="flex justify-end gap-2 border-t border-line pt-3">
              <ActionButton
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsCopyModalOpen(false)}
              >
                Batal
              </ActionButton>
              <ActionButton
                type="button"
                variant="default"
                size="sm"
                disabled={selectedTargetDates.length === 0}
                onClick={executeCopySchedule}
              >
                Terapkan Salinan ({selectedTargetDates.length} Hari)
              </ActionButton>
            </div>
          </div>
        </VmsDialog>
      </FormBlock>
    </QueryState>
  );
};

// ── SUB-KOMPONEN SINGLE DAY FOCUS EDITOR ──────────────────────

interface SingleDayPlanCardProps {
  dayIndex: number;
  totalDays: number;
  control: Control<WeeklyPlanV2Value>;
  register: UseFormRegister<WeeklyPlanV2Value>;
  setValue: UseFormSetValue<WeeklyPlanV2Value>;
  offices: OfficeSiteOption[];
  workTypes: WorkTypeOption[];
  completions: WorkCompletionOption[];
  technicians: TeamMemberOption[];
  onPrevDay: () => void;
  onNextDay: () => void;
  onOpenCopyModal: () => void;
}

const SingleDayPlanCard: React.FC<SingleDayPlanCardProps> = ({
  dayIndex,
  totalDays,
  control,
  register,
  setValue,
  offices,
  workTypes,
  completions,
  technicians,
  onPrevDay,
  onNextDay,
  onOpenCopyModal,
}) => {
  const [showGps, setShowGps] = useState<boolean>(false);
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
      toast.success(`Lokasi site diatur ke: ${found.name}`);
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
      end_time: "17:00:00",
      location_name: "",
      status: "PENDING",
      rollover_approval_status: "NONE",
      assigned_employee_ids: technicians.length > 0 ? [technicians[0].employee_id] : [],
    });
  };

  return (
    <div
      className={`rounded-panel border p-5 shadow-card transition-all space-y-5 ${
        isHoliday
          ? "border-amber-300 bg-amber-50/50 dark:border-amber-900/40 dark:bg-amber-950/20"
          : "border-line bg-surface"
      }`}
    >
      {/* HEADER HARI AKTIF */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
        <div className="flex items-center gap-3">
          <div className="rounded-panel bg-canvas px-3.5 py-1.5 text-center border border-line">
            <TextBlock as="span" className="block text-xs font-semibold uppercase text-primary">
              {dayValue?.work_date ? weekday(dayValue.work_date) : "Hari"}
            </TextBlock>
            <TextBlock as="span" className="block text-sm font-bold text-ink">
              {dayValue?.work_date ? formatDate(dayValue.work_date) : "-"}
            </TextBlock>
          </div>

          <div>
            <TextBlock className="font-semibold text-ink text-sm sm:text-base">
              {isHoliday ? "Hari Libur Operasional" : dayValue?.site_name || "Lokasi Belum Diatur"}
            </TextBlock>
            <TextBlock className="text-xs text-mist">
              {isHoliday
                ? "Tidak ada jadwal kerja atau presensi di hari ini."
                : `Jam Kerja: ${dayValue?.clock_in_time?.slice(0, 5) || "08:00"} - ${
                    dayValue?.clock_out_time?.slice(0, 5) || "17:00"
                  } • Radius Presensi: ${dayValue?.attendance_radius_m || 150}m`}
            </TextBlock>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ActionButton
            type="button"
            variant="outline"
            size="sm"
            onClick={toggleHoliday}
            className={`text-xs ${isHoliday ? "border-amber-500 bg-amber-100 text-amber-800" : ""}`}
          >
            {isHoliday ? "✓ Jadikan Hari Kerja" : "Liburkan Hari Ini"}
          </ActionButton>

          {!isHoliday && (
            <ActionButton
              type="button"
              variant="outline"
              size="sm"
              onClick={onOpenCopyModal}
              className="text-xs gap-1"
            >
              <Copy className="h-3 w-3 text-primary" />
              <TextBlock as="span">Salin</TextBlock>
            </ActionButton>
          )}
        </div>
      </div>

      {/* JIKA LIBUR */}
      {isHoliday ? (
        <div className="py-8 text-center space-y-3">
          <TextBlock as="span" className="text-3xl">🌴</TextBlock>
          <TextBlock className="text-sm font-semibold text-amber-800 dark:text-amber-300">
            Hari ini ditandai sebagai Hari Libur
          </TextBlock>
          <TextBlock className="text-xs text-mist max-w-md mx-auto">
            Tim lapangan tidak memiliki kewajiban absensi GPS atau pelaksanaan tugas di hari ini. Jika ingin menjadwalkan pekerjaan, klik tombol &quot;Jadikan Hari Kerja&quot; di atas.
          </TextBlock>
        </div>
      ) : (
        /* JIKA HARI KERJA */
        <div className="space-y-5">
          {/* BARIS LOKASI & JAM KERJA RINGKAS */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <FormBlock>
              <ControlLabel htmlFor={`days_${dayIndex}_preset`}>Preset Lokasi / Kantor</ControlLabel>
              <ControlSelect
                id={`days_${dayIndex}_preset`}
                defaultValue=""
                onChange={(e) => handleSelectOffice(e.target.value)}
              >
                <ControlOption value="">-- Pilih Lokasi Preset --</ControlOption>
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
                placeholder="Contoh: Site STO Telkom Minas"
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

          {/* TOGGLE PENGATURAN GPS OPSIONAL */}
          <div>
            <PlainAction
              type="button"
              onClick={() => setShowGps(!showGps)}
              className="text-xs text-primary font-medium flex items-center gap-1 hover:underline"
            >
              {showGps ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              <TextBlock as="span">{showGps ? "Sembunyikan Pengaturan GPS" : "⚙️ Pengaturan GPS & Radius Presensi (Opsional)"}</TextBlock>
            </PlainAction>

            {showGps && (
              <div className="mt-3 grid grid-cols-3 gap-3 rounded-panel border border-line bg-canvas p-3">
                <FormBlock>
                  <ControlLabel htmlFor={`days_${dayIndex}_lat`} className="text-xs">Latitude GPS</ControlLabel>
                  <ControlInput
                    id={`days_${dayIndex}_lat`}
                    type="number"
                    step="any"
                    {...register(`days.${dayIndex}.site_lat`, { valueAsNumber: true })}
                    className="text-xs"
                  />
                </FormBlock>

                <FormBlock>
                  <ControlLabel htmlFor={`days_${dayIndex}_lng`} className="text-xs">Longitude GPS</ControlLabel>
                  <ControlInput
                    id={`days_${dayIndex}_lng`}
                    type="number"
                    step="any"
                    {...register(`days.${dayIndex}.site_lng`, { valueAsNumber: true })}
                    className="text-xs"
                  />
                </FormBlock>

                <FormBlock>
                  <ControlLabel htmlFor={`days_${dayIndex}_radius`} className="text-xs">Radius Presensi (Meter)</ControlLabel>
                  <ControlInput
                    id={`days_${dayIndex}_radius`}
                    type="number"
                    min={10}
                    {...register(`days.${dayIndex}.attendance_radius_m`, { valueAsNumber: true })}
                    className="text-xs"
                  />
                </FormBlock>
              </div>
            )}
          </div>

          {/* SUB-SECTION: DAFTAR BUTIR TUGAS */}
          <div className="rounded-panel border border-line bg-canvas p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-line pb-2">
              <div className="flex items-center gap-2">
                <Timer className="h-4 w-4 text-primary" />
                <TextBlock className="text-sm font-semibold text-ink">
                  Daftar Tugas Lapangan ({itemFields.length} Tugas)
                </TextBlock>
              </div>
              <ActionButton
                type="button"
                variant="outline"
                size="sm"
                onClick={addItemSlot}
                className="text-xs font-medium gap-1"
              >
                <Plus className="h-3 w-3" />
                <TextBlock as="span">Tambah Tugas</TextBlock>
              </ActionButton>
            </div>

            <div className="space-y-3">
              {itemFields.map((itemField, itemIndex) => (
                <SingleItemSlotRow
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
                <TextBlock className="py-6 text-center text-xs text-mist border border-dashed border-line rounded-panel">
                  Belum ada tugas lapangan yang dijadwalkan di hari ini. Klik &quot;+ Tambah Tugas&quot; di atas.
                </TextBlock>
              )}
            </div>
          </div>
        </div>
      )}

      {/* NAVIGASI PINDAH HARI SEBELUMNYA / BERIKUTNYA */}
      <div className="flex items-center justify-between border-t border-line pt-3 text-xs">
        <ActionButton
          type="button"
          variant="outline"
          size="sm"
          disabled={dayIndex === 0}
          onClick={onPrevDay}
          className="gap-1"
        >
          <ArrowLeft className="h-3 w-3" />
          <TextBlock as="span">Hari Sebelumnya</TextBlock>
        </ActionButton>

        <TextBlock as="span" className="text-mist">
          Hari ke-{dayIndex + 1} dari {totalDays}
        </TextBlock>

        <ActionButton
          type="button"
          variant="outline"
          size="sm"
          disabled={dayIndex >= totalDays - 1}
          onClick={onNextDay}
          className="gap-1"
        >
          <TextBlock as="span">Hari Berikutnya</TextBlock>
          <ArrowRight className="h-3 w-3" />
        </ActionButton>
      </div>
    </div>
  );
};

// ── BARIS ITEM SLOT TUGAS BERSIH & INTUITIF ─────────────────

interface SingleItemSlotRowProps {
  dayIndex: number;
  itemIndex: number;
  control: Control<WeeklyPlanV2Value>;
  register: UseFormRegister<WeeklyPlanV2Value>;
  setValue: UseFormSetValue<WeeklyPlanV2Value>;
  workTypes: WorkTypeOption[];
  completions: WorkCompletionOption[];
  technicians: TeamMemberOption[];
  onRemove: () => void;
}

const SingleItemSlotRow: React.FC<SingleItemSlotRowProps> = ({
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
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);
  const currentAssigned =
    useWatch({
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
    <div className="rounded-panel border border-line bg-surface p-4 shadow-sm transition-all hover:border-primary/40 space-y-3">
      {/* HEADER TUGAS & JUDUL */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <TextBlock as="span" className="text-[11px] font-bold text-primary uppercase">
              Tugas #{itemIndex + 1}
            </TextBlock>
          </div>
          <ControlInput
            type="text"
            placeholder="Aktivitas tugas, misal: Penarikan Drop Core 12 Core Sektor Timur"
            {...register(`days.${dayIndex}.items.${itemIndex}.title`)}
            className="text-xs font-medium"
            required
          />
        </div>
        <PlainAction
          type="button"
          onClick={onRemove}
          className="rounded p-1.5 text-mist hover:bg-red-50 hover:text-red-600 transition-colors mt-4"
          title="Hapus tugas ini"
        >
          <Trash2 className="h-4 w-4" />
        </PlainAction>
      </div>

      {/* BARIS UTAMA: JENIS PEKERJAAN, TARGET UNIT & ORDER KLIEN */}
      <div className="grid gap-3 sm:grid-cols-12">
        <div className="sm:col-span-5">
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
          <ControlLabel className="text-xs">Target Unit</ControlLabel>
          <ControlInput
            type="number"
            step="any"
            min="0.01"
            {...register(`days.${dayIndex}.items.${itemIndex}.target_qty`, { valueAsNumber: true })}
            className="text-xs"
            required
          />
        </div>

        <div className="sm:col-span-5">
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
      </div>

      {/* PENUGASAN TEKNISI CHIP BUTTONS */}
      {technicians.length > 0 && (
        <div className="border-t border-line/60 pt-2">
          <TextBlock as="span" className="text-[11px] font-medium text-mist block mb-1.5">
            Pilih Teknisi Pelaksana di Tugas Ini:
          </TextBlock>
          <div className="flex flex-wrap gap-1.5">
            {technicians.map((t) => {
              const isSelected = currentAssigned.includes(t.employee_id);
              return (
                <PlainAction
                  key={t.employee_id}
                  type="button"
                  onClick={() => toggleTech(t.employee_id)}
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors ${
                    isSelected
                      ? "border-primary bg-primary text-white font-semibold shadow-xs"
                      : "border-line bg-canvas text-mist hover:text-ink hover:border-line/80"
                  }`}
                >
                  {isSelected ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                  <TextBlock as="span">{t.full_name}</TextBlock>
                </PlainAction>
              );
            })}
          </div>
        </div>
      )}

      {/* TOGGLE WAKTU SLOT & TITIK SPESIFIK */}
      <div>
        <PlainAction
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-[11px] text-mist hover:text-primary flex items-center gap-1"
        >
          {showAdvanced ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          <TextBlock as="span">{showAdvanced ? "Sembunyikan Jam & Posisi" : "⚙️ Jam Slot & Posisi Tiang (Opsional)"}</TextBlock>
        </PlainAction>

        {showAdvanced && (
          <div className="mt-2 grid gap-2 sm:grid-cols-3 rounded-md border border-line bg-canvas p-2.5 text-xs">
            <div>
              <ControlLabel className="text-[11px]">Jam Mulai Slot</ControlLabel>
              <ControlInput
                type="time"
                {...register(`days.${dayIndex}.items.${itemIndex}.start_time`)}
                className="text-xs"
              />
            </div>
            <div>
              <ControlLabel className="text-[11px]">Jam Selesai Slot</ControlLabel>
              <ControlInput
                type="time"
                {...register(`days.${dayIndex}.items.${itemIndex}.end_time`)}
                className="text-xs"
              />
            </div>
            <div>
              <ControlLabel className="text-[11px]">Titik / Posisi Tiang</ControlLabel>
              <ControlInput
                type="text"
                placeholder="Contoh: ODP-MDN-01"
                {...register(`days.${dayIndex}.items.${itemIndex}.location_name`)}
                className="text-xs"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
