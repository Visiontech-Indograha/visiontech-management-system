import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useSession } from "@/app/session";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/PageHeader";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { STATUS_LABEL } from "@/lib/labels";
import { useTransition, useWorkPlans, type WorkPlan } from "./api";
import { CreatePlanDialog } from "./PlanForms";

const PLAN_STATUSES = ["DRAFT", "PUBLISHED", "APPEALED", "ACCEPTED", "IN_PROGRESS", "COMPLETION_REVIEW", "COMPLETED", "CANCELLED"];
const selectCls = "h-11 w-full rounded-control border border-line bg-surface px-3 text-sm md:w-auto";

/** Daftar SK yang terlihat oleh pengguna (GET /work-plans; API menyaring sesuai kedudukan). */
export function WorkPlansPage() {
  const { me } = useSession();
  const canManage = !!me?.permissions.includes("create:plan");
  const [status, setStatus] = useState("");
  const [archived, setArchived] = useState(false);
  const [creating, setCreating] = useState(false);
  const plans = useWorkPlans({ status, archived });

  return (
    <>
      <PageHeader title="Work plan" action={canManage && <Button onClick={() => setCreating(true)}>Buat SK</Button>} />
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center">
        <select aria-label="Filter status" className={selectCls} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Semua status</option>
          {PLAN_STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABEL[s]}
            </option>
          ))}
        </select>
        {canManage && (
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input type="checkbox" className="size-5" checked={archived} onChange={(e) => setArchived(e.target.checked)} />
            Tampilkan draft terarsip
          </label>
        )}
      </div>

      <QueryState
        query={plans}
        errorText="Daftar work plan tidak dapat dimuat."
        empty={plans.data?.length === 0}
        emptyText={archived ? "Tidak ada draft terarsip." : "Belum ada work plan yang dapat Anda lihat."}
        emptyAction={canManage && !archived && <Button onClick={() => setCreating(true)}>Buat SK</Button>}
      >
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {plans.data?.map((p) => (
            <li key={p.id}>
              {archived ? (
                <ArchivedDraft plan={p} />
              ) : (
              <Link
                to={`/work-plans/${p.id}`}
                className="block h-full rounded-panel border border-line bg-surface p-4 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <span className="font-medium text-lens">{p.title}</span>
                  <StatusBadge status={p.status} />
                </div>
                <p className="text-sm text-mist">{p.number ?? "Nomor terbit saat SK diterbitkan"}</p>
                <p className="text-sm text-mist">{p.location_text}</p>
                <p className="text-sm text-mist">
                  {formatDate(p.period_start)} – {formatDate(p.period_end)}
                </p>
              </Link>
              )}
            </li>
          ))}
        </ul>
      </QueryState>

      {creating && <CreatePlanDialog onClose={() => setCreating(false)} />}
    </>
  );
}

/** Draft terarsip tidak dapat dibuka (GET /work-plans/{id} hanya SK aktif); pulihkan dari sini. */
function ArchivedDraft({ plan }: { plan: WorkPlan }) {
  const restore = useTransition(plan.id);
  const onRestore = async () => {
    try {
      await restore.mutateAsync({ action: "restore", row_version: plan.row_version });
      toast.success("Draft dipulihkan.");
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };
  return (
    <div className="flex h-full flex-col gap-2 rounded-panel border border-line bg-surface p-4">
      <span className="font-medium">{plan.title}</span>
      <p className="text-sm text-mist">
        {plan.location_text} · {formatDate(plan.period_start)} – {formatDate(plan.period_end)}
      </p>
      <Button variant="outline" onClick={onRestore} disabled={restore.isPending}>
        Pulihkan draft
      </Button>
    </div>
  );
}
