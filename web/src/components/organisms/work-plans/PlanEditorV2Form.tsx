/**
 * web/src/components/organisms/work-plans/PlanEditorV2Form.tsx
 * Formulir Rencana Kerja V2 Sederhana, Intuitif, dan Cepat (Daily-First Architecture):
 * - Alur 1-Halaman Terarah: Tanpa stepper rumit yang membingungkan
 * - Pola Template 1-Klik: Terapkan lokasi & aktivitas utama ke Senin-Jumat secara otomatis
 * - Tinjauan 7 Hari Bersih: Kartu harian ringkas dengan toggle libur cepat & accordion detail
 * - Bebas Galat DOM Nesting: Menggunakan elemen form native standar tanpa form bersarang
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
import {
  Calendar,
  CalendarClock,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Plus,
  Sparkles,
  Trash2,
  User,
  Users,
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

  const currentIso = useMemo(() => getCurrentIsoWeek(), []);
  const defaultWeekRange = useMemo(
    () => getIsoWeekRange(currentIso.year, currentIso.week),
    [currentIso]
  );

  const nextIso = useMemo(() => {
    const nextWeek = currentIso.week + 1 > 52 ? 1 : currentIso.week + 1;
    const nextYear = currentIso.week + 1 > 52 ? currentIso.year + 1 : currentIso.year;
    return { year: nextYear, week: nextWeek };
  }, [currentIso]);

  const nextWeekRange = useMemo(
    () => getIsoWeekRange(nextIso.year, nextIso.week),
    [nextIso]
  );

  // State untuk preset cepat pengisian
  const [quickSitePreset, setQuickSitePreset] = useState<string>("");
  const [quickWorkTypeId, setQuickWorkTypeId] = useState<string>("");
  const [quickTitle, setQuickTitle] = useState<string>("Pekerjaan Pemeliharaan & Instalasi Lapangan");
  const [quickCompletionId, setQuickCompletionId] = useState<string>("");

  // Accordion state untuk hari yang dibuka detailnya (null = tertutup semua)
  const [expandedDayIndex, setExpandedDayIndex] = useState<number | null>(0);

  // Toggle bagian logistik & alat kerja opsional
  const [showLogistics, setShowLogistics] = useState<boolean>(false);

  // Mode pemilih pekan: "current" | "next" | "custom"
  const [weekSelectionMode, setWeekSelectionMode] = useState<"current" | "next" | "custom">("current");

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

  const selectedQuickWorkTypeId = quickWorkTypeId || filteredWorkTypes[0]?.work_type_id || "";

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

  // Handler pemilihan mode pekan (Pekan Ini vs Pekan Depan)
  const handleSelectWeekMode = (mode: "current" | "next" | "custom") => {
    setWeekSelectionMode(mode);
    if (mode === "current") {
      setValue("week_number", currentIso.week);
      setValue("year", currentIso.year);
      setValue("start_date", defaultWeekRange.start);
      setValue("end_date", defaultWeekRange.end);
    } else if (mode === "next") {
      setValue("week_number", nextIso.week);
      setValue("year", nextIso.year);
      setValue("start_date", nextWeekRange.start);
      setValue("end_date", nextWeekRange.end);
    }
  };

  // ⚡ SMART AUTOFILL: Terapkan template dasar ke seluruh hari kerja (Senin s/d Jumat)
  const handleApplyTemplateToWorkdays = () => {
    const current = getValues("days");
    if (!current || current.length === 0) return;

    const selectedOffice = opts?.offices.find((o) => o.office_id === quickSitePreset);
    const siteName = selectedOffice?.name || "Site Area Proyek";
    const siteLat = selectedOffice?.latitude || 3.5952;
    const siteLng = selectedOffice?.longitude || 98.6722;
    const radius = selectedOffice?.radius_m || 150;
    const wtId = selectedQuickWorkTypeId;
    const compId = quickCompletionId ? quickCompletionId : null;
    const assignedIds = activeTeam?.members.map((m) => m.employee_id) || [];
    if (activeTeam?.leader_employee_id && !assignedIds.includes(activeTeam.leader_employee_id)) {
      assignedIds.unshift(activeTeam.leader_employee_id);
    }

    const updated = current.map((day) => {
      const dObj = new Date(`${day.work_date}T00:00:00Z`);
      const isWeekend = dObj.getUTCDay() === 0 || dObj.getUTCDay() === 6;

      if (isWeekend) {
        return {
          ...day,
          status: "HOLIDAY" as const,
          is_holiday: true,
          items: [],
        };
      }

      const templateItem: PlanItemV2Value = {
        title: quickTitle || "Pekerjaan Lapangan",
        work_type_id: wtId,
        task_phase: "MAIN_INSTALLATION",
        is_main_deliverable: true,
        completion_id: compId,
        target_qty: 1,
        completed_qty: 0,
        progress_percent: 0,
        start_time: "08:00:00",
        end_time: "17:00:00",
        status: "PENDING",
        rollover_approval_status: "NONE",
        assigned_employee_ids: assignedIds,
      };

      return {
        ...day,
        site_name: siteName,
        site_lat: siteLat,
        site_lng: siteLng,
        attendance_radius_m: radius,
        clock_in_time: "08:00:00",
        clock_out_time: "17:00:00",
        status: "SCHEDULED" as const,
        is_holiday: false,
        items: [templateItem],
      };
    });

    replaceDays(updated);
    toast.success("⚡ Berhasil menerapkan template pekerjaan ke seluruh hari kerja (Senin - Jumat)!");
  };

  // Toggle libur untuk 1 hari tertentu
  const handleToggleDayHoliday = (dayIdx: number) => {
    const current = getValues("days");
    if (!current || !current[dayIdx]) return;
    const day = current[dayIdx];
    const nextIsHoliday = !day.is_holiday;

    setValue(`days.${dayIdx}.is_holiday`, nextIsHoliday);
    setValue(`days.${dayIdx}.status`, nextIsHoliday ? "HOLIDAY" : "SCHEDULED");

    if (!nextIsHoliday && (!day.items || day.items.length === 0)) {
      setValue(`days.${dayIdx}.items`, [
        {
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
          assigned_employee_ids: availableTechnicians.map((t) => t.employee_id),
        },
      ]);
    }
  };

  const createMut = useCreateWeeklyPlanV2();
  const updateMut = useUpdateWeeklyPlanV2(planId ?? "");
  const isPending = createMut.isPending || updateMut.isPending || isSubmitting;

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const sanitizedDays = (values.days || []).map((day) => ({
        ...day,
        division_id: day.division_id || values.division_id,
        team_id: day.team_id || values.team_id,
        items: (day.items || []).map((it) => ({
          ...it,
          completion_id: it.completion_id ? it.completion_id : null,
          depends_on_item_id: it.depends_on_item_id ? it.depends_on_item_id : null,
          start_time: it.start_time ? it.start_time : null,
          end_time: it.end_time ? it.end_time : null,
          location_name: it.location_name ? it.location_name : null,
        })),
      }));

      const sanitizedPayload: WeeklyPlanV2Value = {
        ...values,
        vehicle_id: values.vehicle_id ? values.vehicle_id : null,
        driver_employee_id: values.driver_employee_id ? values.driver_employee_id : null,
        days: sanitizedDays,
      };

      if (planId) {
        await updateMut.mutateAsync(sanitizedPayload);
        toast.success("Rencana kerja mingguan berhasil diperbarui!");
        navigate(`/work-plans/${planId}`);
      } else {
        const created = await createMut.mutateAsync(sanitizedPayload);
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

        {/* ── KARTU 1: TIM PELAKSANA & PERIODE PEKAN ─────────────────── */}
        <section
          aria-label="Identitas Tim & Periode"
          className="rounded-panel border border-line bg-surface p-5 shadow-card space-y-4"
        >
          <div className="flex items-center gap-2.5 border-b border-line pb-3">
            <div className="size-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Users className="h-4 w-4" />
            </div>
            <div>
              <TextBlock as="h2" className="text-sm sm:text-base font-semibold text-ink">
                1. Tim Pelaksana &amp; Periode Kerja
              </TextBlock>
              <TextBlock className="text-xs text-mist">
                Tentukan divisi, tim teknisi lapangan, dan rentang pekan kerja rencana ini.
              </TextBlock>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
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
            </div>

            <div className="space-y-1.5">
              <ControlLabel htmlFor="team_id">Tim Kerja Lapangan</ControlLabel>
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
            </div>
          </div>

          {/* Banner Tim Terpilih */}
          {activeTeam && (
            <div className="rounded-panel border border-primary/20 bg-primary/5 p-3.5 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-primary" />
                  <TextBlock className="text-xs font-semibold text-ink">
                    Ketua Tim: {activeTeam.leader_name || "Belum ditentukan"}
                  </TextBlock>
                  <TextBlock as="span" className="text-[10px] text-mist">
                    ({activeTeam.leader_position || "Team Leader"})
                  </TextBlock>
                </div>
                <TextBlock className="text-xs font-medium text-primary">
                  {activeTeam.members.length} Teknisi Lapangan Terdaftar
                </TextBlock>
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {activeTeam.members.map((m) => (
                  <TextBlock
                    as="span"
                    key={m.employee_id}
                    className="inline-flex items-center gap-1 rounded bg-surface border border-line px-2 py-0.5 text-xs text-ink shadow-xs"
                  >
                    <TextBlock as="span">{m.full_name}</TextBlock>
                    <TextBlock as="span" className="text-[10px] text-mist">({m.position})</TextBlock>
                  </TextBlock>
                ))}
              </div>
            </div>
          )}

          {/* Pemilihan Pekan Cepat & Mudah */}
          <div className="border-t border-line pt-3 space-y-2.5">
            <ControlLabel>Periode Pelaksanaan Pekerjaan</ControlLabel>
            <div className="flex flex-wrap items-center gap-2">
              <PlainAction
                type="button"
                onClick={() => handleSelectWeekMode("current")}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-panel border text-xs font-medium transition-colors ${
                  weekSelectionMode === "current"
                    ? "border-primary bg-primary text-white shadow-xs"
                    : "border-line bg-canvas text-mist hover:text-ink hover:bg-surface"
                }`}
              >
                <CalendarClock className="h-3.5 w-3.5" />
                <TextBlock as="span">
                  Pekan Ini ({formatDate(defaultWeekRange.start)} - {formatDate(defaultWeekRange.end)})
                </TextBlock>
              </PlainAction>

              <PlainAction
                type="button"
                onClick={() => handleSelectWeekMode("next")}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-panel border text-xs font-medium transition-colors ${
                  weekSelectionMode === "next"
                    ? "border-primary bg-primary text-white shadow-xs"
                    : "border-line bg-canvas text-mist hover:text-ink hover:bg-surface"
                }`}
              >
                <Calendar className="h-3.5 w-3.5" />
                <TextBlock as="span">
                  Pekan Depan ({formatDate(nextWeekRange.start)} - {formatDate(nextWeekRange.end)})
                </TextBlock>
              </PlainAction>

              <PlainAction
                type="button"
                onClick={() => handleSelectWeekMode("custom")}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-panel border text-xs font-medium transition-colors ${
                  weekSelectionMode === "custom"
                    ? "border-primary bg-primary text-white shadow-xs"
                    : "border-line bg-canvas text-mist hover:text-ink hover:bg-surface"
                }`}
              >
                <TextBlock as="span">Pilih Tanggal Manual...</TextBlock>
              </PlainAction>
            </div>

            {/* Jika mode kustom dipilih */}
            {weekSelectionMode === "custom" && (
              <div className="mt-3 grid gap-3 sm:grid-cols-2 rounded-panel border border-line bg-canvas p-3">
                <div className="space-y-1">
                  <ControlLabel htmlFor="start_date" className="text-xs">Tanggal Mulai (Senin)</ControlLabel>
                  <ControlInput id="start_date" type="date" {...register("start_date")} className="text-xs" />
                  {errors.start_date && <FormErrorText message={errors.start_date.message} />}
                </div>
                <div className="space-y-1">
                  <ControlLabel htmlFor="end_date" className="text-xs">Tanggal Selesai (Minggu)</ControlLabel>
                  <ControlInput id="end_date" type="date" {...register("end_date")} className="text-xs" />
                  {errors.end_date && <FormErrorText message={errors.end_date.message} />}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ── KARTU 2: POLA PEKERJAAN & TEMPLATE OTOMATIS (SMART AUTOFILL) ─ */}
        <section
          aria-label="Pengaturan Cepat Pola Kerja"
          className="rounded-panel border border-primary/30 bg-primary/5 p-5 shadow-sm space-y-4"
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-primary/20 pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <div>
                <TextBlock as="h2" className="text-sm sm:text-base font-semibold text-ink">
                  2. Atur Cepat Jadwal Mingguan (Template Otomatis)
                </TextBlock>
                <TextBlock className="text-xs text-mist">
                  Tentukan lokasi &amp; tugas utama di bawah, lalu klik tombol petir untuk mengisi Senin s/d Jumat sekaligus.
                </TextBlock>
              </div>
            </div>
            <ActionButton
              type="button"
              variant="default"
              size="sm"
              onClick={handleApplyTemplateToWorkdays}
              className="gap-2 shadow-xs shrink-0"
            >
              <Sparkles className="h-4 w-4" />
              <TextBlock as="span">⚡ Terapkan ke Senin - Jumat</TextBlock>
            </ActionButton>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1">
              <ControlLabel className="text-xs font-medium">Lokasi Site / Kantor</ControlLabel>
              <ControlSelect
                value={quickSitePreset}
                onChange={(e) => setQuickSitePreset(e.target.value)}
                className="text-xs bg-surface"
              >
                <ControlOption value="">-- Pilih Kantor / Site Preset --</ControlOption>
                {opts?.offices.map((o) => (
                  <ControlOption key={o.office_id} value={o.office_id}>
                    {o.name}
                  </ControlOption>
                ))}
              </ControlSelect>
            </div>

            <div className="space-y-1">
              <ControlLabel className="text-xs font-medium">Jenis Pekerjaan Utama</ControlLabel>
              <ControlSelect
                value={selectedQuickWorkTypeId}
                onChange={(e) => setQuickWorkTypeId(e.target.value)}
                className="text-xs bg-surface"
              >
                {filteredWorkTypes.map((wt) => (
                  <ControlOption key={wt.work_type_id} value={wt.work_type_id}>
                    {wt.name}
                  </ControlOption>
                ))}
              </ControlSelect>
            </div>

            <div className="space-y-1">
              <ControlLabel className="text-xs font-medium">Aktivitas Pekerjaan</ControlLabel>
              <ControlInput
                type="text"
                value={quickTitle}
                onChange={(e) => setQuickTitle(e.target.value)}
                placeholder="Misal: Penarikan FO & Pemasangan ODP"
                className="text-xs bg-surface"
              />
            </div>

            <div className="space-y-1">
              <ControlLabel className="text-xs font-medium">Kaitan Order Klien (Opsional)</ControlLabel>
              <ControlSelect
                value={quickCompletionId}
                onChange={(e) => setQuickCompletionId(e.target.value)}
                className="text-xs bg-surface"
              >
                <ControlOption value="">-- Tanpa Order Spesifik --</ControlOption>
                {filteredCompletions.map((c) => (
                  <ControlOption key={c.completion_id} value={c.completion_id}>
                    [{c.client_name}] {c.project_title}
                  </ControlOption>
                ))}
              </ControlSelect>
            </div>
          </div>
        </section>

        {/* ── KARTU 3: RINCIAN JADWAL 7 HARI (BERSIH & INTUITIF) ─────── */}
        <section
          aria-label="Rincian 7 Hari Kerja"
          className="rounded-panel border border-line bg-surface p-5 shadow-card space-y-4"
        >
          <div className="flex items-center justify-between border-b border-line pb-3">
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                <Calendar className="h-4 w-4" />
              </div>
              <div>
                <TextBlock as="h2" className="text-sm sm:text-base font-semibold text-ink">
                  3. Rincian Jadwal 7 Hari ({watchedDays.length} Hari)
                </TextBlock>
                <TextBlock className="text-xs text-mist">
                  Senin s/d Jumat aktif sebagai hari kerja. Anda bebas meliburkan hari atau menyesuaikan tugas khusus per hari.
                </TextBlock>
              </div>
            </div>
            <TextBlock as="span" className="text-xs text-mist hidden sm:block">
              {watchedDays.filter((d) => !d.is_holiday).length} Hari Kerja • {watchedDays.filter((d) => d.is_holiday).length} Hari Libur
            </TextBlock>
          </div>

          <div className="space-y-3">
            {dayFields.map((field, dayIdx) => {
              const day = watchedDays[dayIdx];
              const isHoliday = day?.is_holiday || day?.status === "HOLIDAY";
              const isExpanded = expandedDayIndex === dayIdx;
              const itemCount = day?.items?.length || 0;

              return (
                <div
                  key={field.id}
                  className={`rounded-panel border transition-all ${
                    isHoliday
                      ? "border-amber-200 bg-amber-50/40 dark:border-amber-900/30 dark:bg-amber-950/20"
                      : isExpanded
                      ? "border-primary/50 bg-canvas shadow-xs"
                      : "border-line bg-surface hover:border-line/80"
                  }`}
                >
                  {/* BARIS RINGKASAN HARI */}
                  <div className="flex flex-wrap items-center justify-between gap-3 p-3.5">
                    {/* Kolom 1: Tanggal & Nama Hari */}
                    <div className="flex items-center gap-3 min-w-[180px]">
                      <div
                        className={`size-9 rounded-md flex flex-col items-center justify-center text-center font-bold text-xs ${
                          isHoliday
                            ? "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300"
                            : "bg-primary text-white"
                        }`}
                      >
                        <TextBlock as="span" className="text-[10px] uppercase font-bold leading-none">
                          {day?.work_date ? weekday(day.work_date).slice(0, 3) : "H"}
                        </TextBlock>
                        <TextBlock as="span" className="text-xs leading-none mt-0.5">
                          {day?.work_date ? day.work_date.slice(8, 10) : "-"}
                        </TextBlock>
                      </div>

                      <div>
                        <TextBlock className="font-semibold text-xs sm:text-sm text-ink">
                          {day?.work_date ? `${weekday(day.work_date)}, ${formatDate(day.work_date)}` : `Hari ${dayIdx + 1}`}
                        </TextBlock>
                        <TextBlock className="text-[11px] text-mist">
                          {isHoliday
                            ? "🌴 Libur Operasional"
                            : `${day?.site_name || "Site Belum Diatur"} • ${day?.clock_in_time?.slice(0, 5) || "08:00"} - ${
                                day?.clock_out_time?.slice(0, 5) || "17:00"
                              }`}
                        </TextBlock>
                      </div>
                    </div>

                    {/* Kolom 2: Ringkasan Tugas */}
                    <div className="flex-1 min-w-[200px] text-xs">
                      {isHoliday ? (
                        <TextBlock as="span" className="text-amber-700 dark:text-amber-300 text-xs italic">
                          Tidak ada penugasan atau kewajiban presensi GPS.
                        </TextBlock>
                      ) : (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <TextBlock
                            as="span"
                            className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-primary/10 text-primary"
                          >
                            {itemCount} Tugas Terjadwal
                          </TextBlock>
                          {day?.items?.[0] && (
                            <TextBlock as="span" className="text-mist truncate max-w-xs">
                              {day.items[0].title}
                            </TextBlock>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Kolom 3: Aksi Cepat */}
                    <div className="flex items-center gap-2">
                      <ActionButton
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleDayHoliday(dayIdx)}
                        className={`text-xs h-8 px-2.5 ${
                          isHoliday
                            ? "border-primary text-primary hover:bg-primary/10"
                            : "border-line text-mist hover:text-amber-700 hover:bg-amber-50"
                        }`}
                      >
                        {isHoliday ? "✓ Jadikan Kerja" : "Liburkan"}
                      </ActionButton>

                      {!isHoliday && (
                        <ActionButton
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => setExpandedDayIndex(isExpanded ? null : dayIdx)}
                          className="text-xs h-8 px-2.5 gap-1 text-ink"
                        >
                          <TextBlock as="span">{isExpanded ? "Tutup" : "Sesuaikan"}</TextBlock>
                          {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        </ActionButton>
                      )}
                    </div>
                  </div>

                  {/* DETAIL HARI (ACCORDION) */}
                  {isExpanded && !isHoliday && (
                    <div className="border-t border-line/80 bg-surface/80 p-4 space-y-4">
                      {/* Baris Site & Jam Kerja */}
                      <div className="grid gap-3 sm:grid-cols-3">
                        <div className="space-y-1">
                          <ControlLabel htmlFor={`days_${dayIdx}_site`} className="text-xs">
                            Nama Site / Lokasi Proyek
                          </ControlLabel>
                          <ControlInput
                            id={`days_${dayIdx}_site`}
                            type="text"
                            placeholder="Misal: STO Minas"
                            {...register(`days.${dayIdx}.site_name`)}
                            className="text-xs"
                            required
                          />
                        </div>

                        <div className="space-y-1">
                          <ControlLabel htmlFor={`days_${dayIdx}_in`} className="text-xs">
                            Jam Masuk
                          </ControlLabel>
                          <ControlInput
                            id={`days_${dayIdx}_in`}
                            type="time"
                            {...register(`days.${dayIdx}.clock_in_time`)}
                            className="text-xs"
                          />
                        </div>

                        <div className="space-y-1">
                          <ControlLabel htmlFor={`days_${dayIdx}_out`} className="text-xs">
                            Jam Pulang
                          </ControlLabel>
                          <ControlInput
                            id={`days_${dayIdx}_out`}
                            type="time"
                            {...register(`days.${dayIdx}.clock_out_time`)}
                            className="text-xs"
                          />
                        </div>
                      </div>

                      {/* Sub-form Butir Tugas Hari Ini */}
                      <DayItemsSubList
                        dayIndex={dayIdx}
                        control={control}
                        register={register}
                        setValue={setValue}
                        workTypes={filteredWorkTypes}
                        completions={filteredCompletions}
                        technicians={availableTechnicians}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* ── KARTU 4: KENDARAAN & ALAT GUDANG (OPSIONAL) ───────────── */}
        <section
          aria-label="Armada & Alat Kerja"
          className="rounded-panel border border-line bg-surface p-5 shadow-card space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                <Wrench className="h-4 w-4" />
              </div>
              <div>
                <TextBlock as="h2" className="text-sm sm:text-base font-semibold text-ink">
                  4. Kendaraan &amp; Peralatan Kerja (Opsional)
                </TextBlock>
                <TextBlock className="text-xs text-mist">
                  Bawa kendaraan operasional atau alat khusus dari gudang.
                </TextBlock>
              </div>
            </div>

            <PlainAction
              type="button"
              onClick={() => setShowLogistics(!showLogistics)}
              className="text-xs text-primary font-medium hover:underline flex items-center gap-1"
            >
              <TextBlock as="span">{showLogistics ? "Sembunyikan" : "Buka Pilihan Logistik"}</TextBlock>
              {showLogistics ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </PlainAction>
          </div>

          {showLogistics && (
            <div className="pt-3 border-t border-line space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <ControlLabel htmlFor="vehicle_id">Armada Operasional</ControlLabel>
                  <ControlSelect id="vehicle_id" {...register("vehicle_id")} className="text-xs">
                    <ControlOption value="">-- Tanpa Kendaraan Operasional --</ControlOption>
                    {opts?.vehicles.map((v) => (
                      <ControlOption key={v.vehicle_id} value={v.vehicle_id}>
                        [{v.vehicle_type}] {v.name} ({v.number_plate})
                      </ControlOption>
                    ))}
                  </ControlSelect>
                </div>

                <div className="space-y-1.5">
                  <ControlLabel htmlFor="driver_employee_id">Pengemudi Ditunjuk</ControlLabel>
                  <ControlSelect id="driver_employee_id" {...register("driver_employee_id")} className="text-xs">
                    <ControlOption value="">-- Pilih Anggota Tim sebagai Driver --</ControlOption>
                    {availableTechnicians.map((t) => (
                      <ControlOption key={t.employee_id} value={t.employee_id}>
                        {t.full_name}
                      </ControlOption>
                    ))}
                  </ControlSelect>
                </div>
              </div>

              {opts?.tools && opts.tools.length > 0 && (
                <div className="space-y-2">
                  <ControlLabel className="text-xs">Peralatan Kerja dari Gudang</ControlLabel>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
                    {opts.tools.map((tool) => (
                      <ControlLabel
                        key={tool.tool_id}
                        className="flex cursor-pointer items-center gap-2 rounded border border-line bg-canvas p-2 text-xs hover:bg-surface transition-colors"
                      >
                        <ControlInput
                          type="checkbox"
                          value={tool.tool_id}
                          {...register("tool_ids")}
                          className="rounded border-line text-primary focus:ring-primary size-4"
                        />
                        <TextBlock as="span" className="truncate font-medium">{tool.name}</TextBlock>
                      </ControlLabel>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* ── FOOTER AKSI SUBMIT ────────────────────────────────────── */}
        <div className="flex items-center justify-between border-t border-line pt-4">
          <ActionButton
            type="button"
            variant="outline"
            onClick={() => navigate("/work-plans")}
          >
            Batal
          </ActionButton>

          <ActionButton type="submit" variant="default" disabled={isPending} className="gap-2">
            <CheckCircle2 className="h-4 w-4" />
            <TextBlock as="span">
              {isPending
                ? "Menyimpan Rencana Kerja..."
                : planId
                ? "Simpan Perubahan Rencana Kerja"
                : "Terbitkan Rencana Kerja Mingguan"}
            </TextBlock>
          </ActionButton>
        </div>
      </FormBlock>
    </QueryState>
  );
};

// ── SUB-KOMPONEN DAFTAR TUGAS HARIAN ──────────────────────────

interface DayItemsSubListProps {
  dayIndex: number;
  control: Control<WeeklyPlanV2Value>;
  register: UseFormRegister<WeeklyPlanV2Value>;
  setValue: UseFormSetValue<WeeklyPlanV2Value>;
  workTypes: WorkTypeOption[];
  completions: WorkCompletionOption[];
  technicians: TeamMemberOption[];
}

const DayItemsSubList: React.FC<DayItemsSubListProps> = ({
  dayIndex,
  control,
  register,
  setValue,
  workTypes,
  completions,
  technicians,
}) => {
  const {
    fields: itemFields,
    append: appendItem,
    remove: removeItem,
  } = useFieldArray({
    control,
    name: `days.${dayIndex}.items`,
  });

  const addItem = () => {
    appendItem({
      title: "Pekerjaan Lapangan",
      work_type_id: workTypes[0]?.work_type_id || "",
      task_phase: "MAIN_INSTALLATION",
      is_main_deliverable: true,
      completion_id: null,
      target_qty: 1,
      completed_qty: 0,
      progress_percent: 0,
      start_time: "08:00:00",
      end_time: "17:00:00",
      status: "PENDING",
      rollover_approval_status: "NONE",
      assigned_employee_ids: technicians.map((t) => t.employee_id),
    });
  };

  return (
    <div className="rounded-panel border border-line bg-canvas p-3 space-y-3">
      <div className="flex items-center justify-between border-b border-line pb-2">
        <TextBlock className="text-xs font-semibold text-ink">
          Daftar Tugas / Aktivitas ({itemFields.length} Tugas)
        </TextBlock>
        <ActionButton
          type="button"
          variant="outline"
          size="sm"
          onClick={addItem}
          className="text-xs h-7 px-2 gap-1"
        >
          <Plus className="h-3 w-3" />
          <TextBlock as="span">Tambah Tugas</TextBlock>
        </ActionButton>
      </div>

      <div className="space-y-2.5">
        {itemFields.map((field, itemIdx) => (
          <DayItemRow
            key={field.id}
            dayIndex={dayIndex}
            itemIndex={itemIdx}
            control={control}
            register={register}
            setValue={setValue}
            workTypes={workTypes}
            completions={completions}
            technicians={technicians}
            onRemove={() => removeItem(itemIdx)}
          />
        ))}

        {itemFields.length === 0 && (
          <TextBlock className="text-center py-4 text-xs text-mist border border-dashed border-line rounded">
            Belum ada tugas di hari ini. Klik &quot;+ Tambah Tugas&quot; di atas.
          </TextBlock>
        )}
      </div>
    </div>
  );
};

// ── BARIS BUTIR TUGAS INDIVIDUAL ──────────────────────────────

interface DayItemRowProps {
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

const DayItemRow: React.FC<DayItemRowProps> = ({
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
    <div className="rounded border border-line bg-surface p-3 space-y-2.5 text-xs shadow-xs">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 flex-1">
          <TextBlock as="span" className="font-bold text-primary">
            #{itemIndex + 1}
          </TextBlock>
          <ControlInput
            type="text"
            placeholder="Aktivitas tugas, misal: Penarikan Drop Core Sektor Barat"
            {...register(`days.${dayIndex}.items.${itemIndex}.title`)}
            className="text-xs h-8 flex-1"
            required
          />
        </div>
        <PlainAction
          type="button"
          onClick={onRemove}
          className="p-1.5 text-mist hover:text-red-600 rounded"
          title="Hapus tugas ini"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </PlainAction>
      </div>

      <div className="grid gap-2 sm:grid-cols-12">
        <div className="sm:col-span-5">
          <ControlLabel className="text-[11px]">Jenis Pekerjaan</ControlLabel>
          <ControlSelect
            {...register(`days.${dayIndex}.items.${itemIndex}.work_type_id`)}
            className="text-xs h-8"
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
          <ControlLabel className="text-[11px]">Target Unit</ControlLabel>
          <ControlInput
            type="number"
            step="any"
            min="0.01"
            {...register(`days.${dayIndex}.items.${itemIndex}.target_qty`, { valueAsNumber: true })}
            className="text-xs h-8"
            required
          />
        </div>

        <div className="sm:col-span-5">
          <ControlLabel className="text-[11px]">Order Klien (Opsional)</ControlLabel>
          <ControlSelect
            {...register(`days.${dayIndex}.items.${itemIndex}.completion_id`)}
            className="text-xs h-8"
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

      {/* Teknisi Pelaksana (Chip) */}
      {technicians.length > 0 && (
        <div className="border-t border-line/60 pt-2">
          <TextBlock as="span" className="text-[10px] text-mist block mb-1">
            Teknisi yang bertugas:
          </TextBlock>
          <div className="flex flex-wrap gap-1">
            {technicians.map((t) => {
              const isSelected = currentAssigned.includes(t.employee_id);
              return (
                <PlainAction
                  key={t.employee_id}
                  type="button"
                  onClick={() => toggleTech(t.employee_id)}
                  className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] transition-colors ${
                    isSelected
                      ? "bg-primary text-white font-medium"
                      : "bg-canvas text-mist hover:text-ink border border-line"
                  }`}
                >
                  {isSelected && <Check className="h-2.5 w-2.5" />}
                  <TextBlock as="span">{t.full_name}</TextBlock>
                </PlainAction>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
