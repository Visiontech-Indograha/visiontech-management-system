import { useMemo, useState } from "react";
import {
  useHesPlans,
  useHesPlanByYear,
  useCreateHesPlan,
  useDeleteHesPlan,
  useUpsertHesIndicators,
  HESLaggingType,
  HESLeadingType,
  HESPlan,
} from "../../hooks/api/useHesPlan";
import { Button } from "../../components/ui/Button";
import { Select, Input } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { LoadingState } from "../../components/ui/QueryState";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

const LAGGING_TYPES: { key: HESLaggingType; label: string }[] = [
  { key: "P3K_CASE", label: "P3K Case" },
  { key: "NEAR_MISS", label: "Near Miss" },
  { key: "RECORDABLE_CASE", label: "Recordable Case" },
  { key: "ENVIRONMENTAL_INCIDENT", label: "Env. Incident" },
  { key: "FIRE_EXPLOSION", label: "Fire / Explosion" },
  { key: "PROPERTY_DAMAGE", label: "Property Damage" },
];

const LEADING_TYPES: { key: HESLeadingType; label: string }[] = [
  { key: "MEETING", label: "Meeting" },
  { key: "INSPECTION_AUDIT", label: "Inspection / Audit" },
  { key: "FIT_FOR_DUTY", label: "Fit For Duty" },
  { key: "HES_CAMPAIGN", label: "HES Campaign" },
  { key: "EMPLOYEE_ORIENTATION", label: "Employee Orientation" },
  { key: "REPORTING", label: "Reporting" },
];

const currentYear = new Date().getFullYear();

const HESPlanPage = () => {
  const { user } = useAuth();
  const canWrite = user?.role === UserRole.ADMIN || user?.role === UserRole.HR_HES;
  const { data: plans } = useHesPlans();
  const [year, setYear] = useState(currentYear);
  const { data: plan, isLoading, error } = useHesPlanByYear(year);
  const createMutation = useCreateHesPlan();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newYear, setNewYear] = useState(currentYear);

  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createMutation.mutateAsync({ year: newYear });
      setYear(newYear);
      setIsCreateOpen(false);
    } catch {
      // Error sudah ditampilkan oleh interceptor global di lib/api.ts
    }
  };

  const years = plans?.map((p) => p.year).sort((a, b) => b - a) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">HES Plan</h1>
          <p className="mt-1 text-sm text-gray-500">Lagging &amp; leading indicator kesehatan, keselamatan, dan lingkungan per tahun.</p>
        </div>
        <div className="flex items-center gap-3">
          <Select label="Tahun" value={String(year)} onChange={(e) => setYear(Number(e.target.value))}>
            {years.length === 0 && <option value={year}>{year}</option>}
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </Select>
          {canWrite && <Button onClick={() => { setNewYear(currentYear); setIsCreateOpen(true); }}>+ Plan Tahun Baru</Button>}
        </div>
      </div>

      {isLoading ? (
        <LoadingState label="Loading HES Plan..." />
      ) : error || !plan ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center">
          <p className="text-gray-500">Belum ada HES Plan untuk tahun {year}.</p>
          {canWrite && (
            <Button className="mt-4" onClick={() => { setNewYear(year); setIsCreateOpen(true); }}>
              Buat HES Plan {year}
            </Button>
          )}
        </div>
      ) : (
        <HesPlanEditor key={plan.id} plan={plan} canWrite={canWrite} year={year} />
      )}

      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Buat HES Plan Baru">
        <form onSubmit={handleCreatePlan} className="space-y-4">
          <Input
            label="Tahun"
            type="number"
            required
            value={newYear}
            onChange={(e) => setNewYear(Number(e.target.value))}
          />
          <ModalFooter onCancel={() => setIsCreateOpen(false)} isSubmitting={createMutation.isPending} />
        </form>
      </Modal>
    </div>
  );
};

const HesPlanEditor = ({ plan, canWrite, year }: { plan: HESPlan; canWrite: boolean; year: number }) => {
  const deleteMutation = useDeleteHesPlan();
  const upsertMutation = useUpsertHesIndicators();

  const [tab, setTab] = useState<"lagging" | "leading">("lagging");
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const [lagValues, setLagValues] = useState<Record<string, number>>(() => {
    const lag: Record<string, number> = {};
    for (const item of plan.lagging_indicators) {
      lag[`${item.indicator_type}-${item.month}`] = item.count;
    }
    return lag;
  });

  const [leadValues, setLeadValues] = useState<Record<string, { actual: number; target: number }>>(() => {
    const lead: Record<string, { actual: number; target: number }> = {};
    for (const item of plan.leading_indicators) {
      lead[`${item.activity_type}-${item.month}`] = { actual: item.actual, target: item.target };
    }
    return lead;
  });

  const laggingChartData = useMemo(() => {
    return MONTHS.map((m, idx) => {
      const month = idx + 1;
      let total = 0;
      for (const t of LAGGING_TYPES) {
        total += lagValues[`${t.key}-${month}`] || 0;
      }
      return { name: m, total };
    });
  }, [lagValues]);

  const leadingChartData = useMemo(() => {
    return MONTHS.map((m, idx) => {
      const month = idx + 1;
      let actual = 0;
      let target = 0;
      for (const t of LEADING_TYPES) {
        const v = leadValues[`${t.key}-${month}`];
        if (v) {
          actual += v.actual;
          target += v.target;
        }
      }
      return { name: m, actual, target };
    });
  }, [leadValues]);

  const handleDeletePlan = async () => {
    await deleteMutation.mutateAsync(plan.id);
    setDeleteConfirm(false);
  };

  const handleSaveLagging = async () => {
    const lagging = LAGGING_TYPES.flatMap((t) =>
      MONTHS.map((_, idx) => ({
        indicator_type: t.key,
        month: idx + 1,
        count: lagValues[`${t.key}-${idx + 1}`] || 0,
      }))
    );
    await upsertMutation.mutateAsync({ planId: plan.id, lagging, leading: [] });
  };

  const handleSaveLeading = async () => {
    const leading = LEADING_TYPES.flatMap((t) =>
      MONTHS.map((_, idx) => {
        const v = leadValues[`${t.key}-${idx + 1}`] || { actual: 0, target: 0 };
        return { activity_type: t.key, month: idx + 1, actual: v.actual, target: v.target };
      })
    );
    await upsertMutation.mutateAsync({ planId: plan.id, lagging: [], leading });
  };

  return (
    <div className="space-y-6">
      {canWrite && (
        <div className="flex justify-end">
          <button onClick={() => setDeleteConfirm(true)} className="text-red-600 hover:underline text-sm">
            Hapus HES Plan {year}
          </button>
        </div>
      )}

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {(["lagging", "leading"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`${tab === t ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"} whitespace-nowrap border-b-2 px-1 pb-4 text-sm font-medium`}
            >
              {t === "lagging" ? "Lagging Indicator" : "Leading Indicator"}
            </button>
          ))}
        </nav>
      </div>

      {tab === "lagging" ? (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-sm font-semibold text-gray-700">Total Kejadian per Bulan</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={laggingChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" fontSize={12} />
                <YAxis fontSize={12} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="total" fill="#dc2626" name="Total Kejadian" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="sticky left-0 bg-gray-50 px-3 py-2 text-left font-medium text-gray-600">Indikator</th>
                  {MONTHS.map((m) => (
                    <th key={m} className="px-2 py-2 text-center font-medium text-gray-600">{m}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {LAGGING_TYPES.map((t) => (
                  <tr key={t.key}>
                    <td className="sticky left-0 bg-white px-3 py-2 font-medium text-gray-700">{t.label}</td>
                    {MONTHS.map((_, idx) => {
                      const month = idx + 1;
                      const key = `${t.key}-${month}`;
                      return (
                        <td key={key} className="px-1 py-1">
                          <input
                            type="number"
                            min={0}
                            disabled={!canWrite}
                            value={lagValues[key] ?? 0}
                            onChange={(e) => setLagValues({ ...lagValues, [key]: Number(e.target.value) })}
                            className="w-14 rounded border border-gray-300 px-1 py-1 text-center text-xs disabled:bg-gray-100"
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {canWrite && (
            <div className="flex justify-end">
              <Button onClick={handleSaveLagging} disabled={upsertMutation.isPending}>
                {upsertMutation.isPending ? "Menyimpan..." : "Simpan Lagging Indicator"}
              </Button>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-sm font-semibold text-gray-700">Aktivitas: Realisasi vs Target per Bulan</h2>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={leadingChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" fontSize={12} />
                <YAxis fontSize={12} allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="actual" stroke="#4f46e5" name="Realisasi" />
                <Line type="monotone" dataKey="target" stroke="#9ca3af" strokeDasharray="4 4" name="Target" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="sticky left-0 bg-gray-50 px-3 py-2 text-left font-medium text-gray-600">Aktivitas</th>
                  {MONTHS.map((m) => (
                    <th key={m} className="px-2 py-2 text-center font-medium text-gray-600">{m}<br /><span className="font-normal text-[10px]">Aktual/Target</span></th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {LEADING_TYPES.map((t) => (
                  <tr key={t.key}>
                    <td className="sticky left-0 bg-white px-3 py-2 font-medium text-gray-700">{t.label}</td>
                    {MONTHS.map((_, idx) => {
                      const month = idx + 1;
                      const key = `${t.key}-${month}`;
                      const v = leadValues[key] || { actual: 0, target: 0 };
                      return (
                        <td key={key} className="px-1 py-1">
                          <div className="flex flex-col gap-0.5">
                            <input
                              type="number"
                              min={0}
                              disabled={!canWrite}
                              value={v.actual}
                              onChange={(e) => setLeadValues({ ...leadValues, [key]: { ...v, actual: Number(e.target.value) } })}
                              className="w-14 rounded border border-gray-300 px-1 py-0.5 text-center text-xs disabled:bg-gray-100"
                            />
                            <input
                              type="number"
                              min={0}
                              disabled={!canWrite}
                              value={v.target}
                              onChange={(e) => setLeadValues({ ...leadValues, [key]: { ...v, target: Number(e.target.value) } })}
                              className="w-14 rounded border border-gray-200 px-1 py-0.5 text-center text-xs text-gray-500 disabled:bg-gray-100"
                            />
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {canWrite && (
            <div className="flex justify-end">
              <Button onClick={handleSaveLeading} disabled={upsertMutation.isPending}>
                {upsertMutation.isPending ? "Menyimpan..." : "Simpan Leading Indicator"}
              </Button>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm}
        message={`Hapus HES Plan tahun ${year} beserta seluruh data indikatornya?`}
        isConfirming={deleteMutation.isPending}
        onConfirm={handleDeletePlan}
        onCancel={() => setDeleteConfirm(false)}
      />
    </div>
  );
};

export default HESPlanPage;
