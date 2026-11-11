import { useState } from "react";
import { toast } from "sonner";
import { DailyPlansTemplate, type DailyDialog } from "@/components/templates/work-plans/DailyPlansTemplate";
import { ApiError } from "@/lib/apiClient";
import { addDays, useBulkApprove, useDailyFormOptions, useDailyPlans, useWeekSurveys, wibDate, weekStart } from "@/services/dailyPlanService";
import { useSession } from "@/stores/sessionStore";

/** "Jadwal harian" (Milestone 5, daily-first): minggu = rentang tanggal Senin–Minggu. */
export function DailyPlansPage() {
  const { me } = useSession();
  const canPlan = !!me?.permissions.includes("create:plan");
  const today = wibDate();
  const [start, setStart] = useState(() => weekStart(today));
  const [divisionId, setDivisionId] = useState("");
  const [dialog, setDialog] = useState<DailyDialog>(null);
  const end = addDays(start, 6);
  const plans = useDailyPlans({ start, end, division_id: divisionId || undefined });
  const surveys = useWeekSurveys({ start, end });
  const options = useDailyFormOptions(canPlan);
  const bulk = useBulkApprove();
  const pending = (plans.data ?? []).filter((p) => (p.status === "SUBMITTED" || p.status === "DRAFT") && p.work_date >= today);

  const approveWeek = () =>
    bulk.mutate(pending.map((p) => p.daily_plan_id), {
      onSuccess: (r) =>
        toast.success(`${r.approved.length} jadwal disetujui${r.skipped.length ? `, ${r.skipped.length} dilewati` : ""}.`),
      onError: (err) => toast.error(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi."),
    });

  return (
    <DailyPlansTemplate
      start={start}
      end={end}
      today={today}
      plans={plans}
      surveys={surveys.data ?? []}
      options={options.data}
      divisionId={divisionId}
      canPlan={canPlan}
      myEmployeeId={me?.employee_id ?? null}
      pendingApproval={pending.length}
      approving={bulk.isPending}
      dialog={dialog}
      onWeek={(delta) => setStart(delta === null ? weekStart(today) : addDays(start, delta))}
      onDivision={setDivisionId}
      onApproveWeek={approveWeek}
      onDialog={setDialog}
    />
  );
}
