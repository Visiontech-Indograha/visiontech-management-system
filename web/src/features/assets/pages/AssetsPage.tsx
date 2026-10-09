import { zodResolver } from "@hookform/resolvers/zod";
import { useState, type ReactNode } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { useSession } from "@/app/session";
import { QueryState } from "@/components/molecules/QueryState";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import { Button } from "@/components/atoms/Button";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { PageHeader } from "@/components/organisms/PageHeader";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { api, ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useActiveEmployees } from "@/features/work-plans/workPlanService";
import { useActivePlans, useAssets, useCheckAsset, useCreateAsset, useAssetReturns, useReleaseAsset, useRequestReturn, useReserveAsset, useVerifyReturn, type Asset, type AssetReturnItem } from "../assetService";

type Open = { kind: "create" } | { kind: "reserve" | "release" | "check" | "return" | "verify" | "history"; asset: Asset } | null;

/** "Kendaraan & alat" (prototype/js/operations.js assets). Aturan alokasi tetap di API. */
export function AssetsPage() {
  const { me } = useSession();
  const perms = me?.permissions ?? [];
  const canManage = perms.includes("manage:assets");
  const canReserve = canManage || perms.includes("create:plan");
  // RETURN_ASSET: ketua SK peminjam (bukan petugas aset); VERIFY_RETURN: petugas aset.
  const isBorrowingLeader = (a: Asset) => !!me?.employee_id && a.leader_employee_id === me.employee_id && !canManage;
  const assets = useAssets();
  const [open, setOpen] = useState<Open>(null);
  const close = () => setOpen(null);

  return (
    <>
      <PageHeader title="Kendaraan & alat" action={canManage && <Button onClick={() => setOpen({ kind: "create" })}>Tambah aset</Button>} />
      <QueryState query={assets} errorText="Daftar aset tidak dapat dimuat." empty={assets.data?.length === 0} emptyText="Belum ada kendaraan atau alat.">
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {assets.data?.map((a) => (
            <li key={a.id} className="flex flex-col gap-2 rounded-panel border border-line bg-surface shadow-card p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold tracking-wide text-mist">{a.kind === "VEHICLE" ? "KENDARAAN" : "PERALATAN"}</span>
                <StatusBadge status={a.status} />
              </div>
              <h2 className="font-medium">{a.name}</h2>
              <dl className="text-sm text-mist">
                <div>Kode: {a.code}</div>
                <div>Kondisi: {a.condition}</div>
                {a.vehicle_type && <div>Jenis: {a.vehicle_type}</div>}
                {a.plan_number && <div>Dipakai: rencana kerja {a.plan_number}</div>}
                {a.pending_return_id && (
                  <div className="mt-1 text-warning">
                    Pengembalian diajukan {a.return_requested_by_name ?? "ketua tim"} · kondisi {a.return_condition}
                    {a.return_note ? ` — ${a.return_note}` : ""}
                  </div>
                )}
              </dl>
              <div className="mt-auto flex flex-col gap-2 md:flex-row md:flex-wrap">
                {canReserve && a.status === "AVAILABLE" && <Button onClick={() => setOpen({ kind: "reserve", asset: a })}>Alokasikan</Button>}
                {canReserve && a.status === "RESERVED" && (
                  <Button variant="outline" onClick={() => setOpen({ kind: "release", asset: a })}>
                    Lepas reservasi
                  </Button>
                )}
                {isBorrowingLeader(a) && a.allocation_id && !a.pending_return_id && ["IN_USE", "RESERVED"].includes(a.status) && (
                  <Button variant="outline" onClick={() => setOpen({ kind: "return", asset: a })}>
                    Ajukan pengembalian
                  </Button>
                )}
                {canManage && a.status === "RETURN_PENDING" && a.pending_return_id && (
                  <Button onClick={() => setOpen({ kind: "verify", asset: a })}>Periksa pengembalian</Button>
                )}
                <Button variant="ghost" onClick={() => setOpen({ kind: "history", asset: a })}>
                  Riwayat
                </Button>
                {a.kind === "VEHICLE" && a.status === "RESERVED" && (
                  <Button variant="outline" onClick={() => setOpen({ kind: "check", asset: a })}>
                    Periksa Kendaraan
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </QueryState>
      {open?.kind === "create" && <CreateAssetDialog onClose={close} />}
      {open?.kind === "reserve" && <ReserveDialog asset={open.asset} onClose={close} />}
      {open?.kind === "release" && <ReleaseDialog asset={open.asset} onClose={close} />}
      {open?.kind === "check" && <CheckDialog asset={open.asset} onClose={close} />}
      {open?.kind === "return" && <ReturnDialog asset={open.asset} onClose={close} />}
      {open?.kind === "verify" && <VerifyReturnDialog asset={open.asset} onClose={close} />}
      {open?.kind === "history" && <ReturnHistoryDialog asset={open.asset} onClose={close} />}
    </>
  );
}

function FormDialog({
  title,
  submitLabel = "Simpan",
  submitting,
  formError,
  onClose,
  onSubmit,
  children,
}: {
  title: string;
  submitLabel?: string;
  submitting: boolean;
  formError: string | null;
  onClose: () => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}) {
  return (
    <VmsDialog
      open
      title={title}
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Batal
          </Button>
          <Button type="submit" form="asset-form" disabled={submitting}>
            {submitting ? "Menyimpan..." : submitLabel}
          </Button>
        </>
      }
    >
      <form id="asset-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        {children}
      </form>
    </VmsDialog>
  );
}

const createSchema = z
  .object({
    kind: z.enum(["VEHICLE", "TOOL"]),
    vehicle_type: z.string().trim(),
    code: z.string().trim().min(1, "Kode aset wajib diisi."),
    name: z.string().trim().min(1, "Nama aset wajib diisi."),
    condition: z.string().trim().min(1, "Kondisi wajib diisi."),
  })
  .refine((v) => v.kind === "TOOL" || v.vehicle_type.length > 0, { path: ["vehicle_type"], message: "Jenis kendaraan wajib diisi." });
type CreateValues = z.infer<typeof createSchema>;

function CreateAssetDialog({ onClose }: { onClose: () => void }) {
  const create = useCreateAsset();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { kind: "VEHICLE", vehicle_type: "", code: "", name: "", condition: "Baik" },
  });
  const kind = useWatch({ control, name: "kind" });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await create.mutateAsync({ ...v, vehicle_type: v.kind === "VEHICLE" ? v.vehicle_type : null });
      toast.success("Aset ditambahkan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title="Tambah aset" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <SelectField label="Jenis aset" {...register("kind")}>
        <option value="VEHICLE">Kendaraan</option>
        <option value="TOOL">Peralatan</option>
      </SelectField>
      {kind === "VEHICLE" && <TextField label="Jenis kendaraan" hint="Contoh: Pick-up, Minibus" error={errors.vehicle_type?.message} {...register("vehicle_type")} />}
      <TextField label="Kode aset" error={errors.code?.message} {...register("code")} />
      <TextField label="Nama aset" error={errors.name?.message} {...register("name")} />
      <TextField label="Kondisi" error={errors.condition?.message} {...register("condition")} />
    </FormDialog>
  );
}

function PlanSelect({ error, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { error?: string; ref?: React.Ref<HTMLSelectElement> }) {
  const plans = useActivePlans();
  return (
    <SelectField label="Work plan" error={error} hint={plans.isError ? "Daftar work plan tidak dapat dimuat." : undefined} {...props}>
      <option value="">{plans.isPending ? "Memuat..." : "Pilih work plan"}</option>
      {plans.data?.map((p) => (
        <option key={p.id} value={p.id}>
          {p.number ? `${p.number} · ` : ""}
          {p.title}
        </option>
      ))}
    </SelectField>
  );
}

function ReserveDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const reserve = useReserveAsset();
  const employees = useActiveEmployees();
  const vehicle = asset.kind === "VEHICLE";
  const schema = z
    .object({ work_plan_id: z.string().min(1, "Pilih work plan."), driver_employee_id: z.string() })
    .refine((v) => !vehicle || v.driver_employee_id.length > 0, { path: ["driver_employee_id"], message: "Pilih pengemudi untuk aset kendaraan." });
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { work_plan_id: "", driver_employee_id: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await reserve.mutateAsync({ id: asset.id, work_plan_id: v.work_plan_id, driver_employee_id: vehicle ? v.driver_employee_id : null });
      toast.success("Aset dialokasikan.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title={`Alokasikan ${asset.name}`} submitLabel="Alokasikan" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <PlanSelect error={errors.work_plan_id?.message} {...register("work_plan_id")} />
      {vehicle && (
        <SelectField label="Pengemudi" hint="Harus anggota tim penugasan." error={errors.driver_employee_id?.message} {...register("driver_employee_id")}>
          <option value="">{employees.isPending ? "Memuat..." : "Pilih pengemudi"}</option>
          {employees.data?.map((e) => (
            <option key={e.id} value={e.id}>
              {e.full_name}
            </option>
          ))}
        </SelectField>
      )}
    </FormDialog>
  );
}

const releaseSchema = z.object({ work_plan_id: z.string().min(1, "Pilih work plan.") });

function ReleaseDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const release = useReleaseAsset();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ work_plan_id: string }>({ resolver: zodResolver(releaseSchema), defaultValues: { work_plan_id: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await release.mutateAsync({ id: asset.id, work_plan_id: v.work_plan_id });
      toast.success("Reservasi dilepas.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title={`Lepas reservasi ${asset.name}`} submitLabel="Lepas reservasi" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <p className="mb-3 text-sm text-mist">Pilih work plan yang memesan aset ini.</p>
      <PlanSelect error={errors.work_plan_id?.message} {...register("work_plan_id")} />
    </FormDialog>
  );
}

const checkSchema = z
  .object({ decision: z.enum(["ACCEPT", "APPEAL"]), reason: z.string().trim() })
  .refine((v) => v.decision === "ACCEPT" || v.reason.length > 0, { path: ["reason"], message: "Alasan banding kelayakan wajib diisi." });
type CheckValues = z.infer<typeof checkSchema>;

/** Pengemudi yang ditunjuk menyatakan kendaraan layak (ACCEPT) atau banding (APPEAL). */
function CheckDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const check = useCheckAsset();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CheckValues>({ resolver: zodResolver(checkSchema), defaultValues: { decision: "ACCEPT", reason: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await check.mutateAsync({ id: asset.id, decision: v.decision, reason: v.reason || null });
      toast.success(v.decision === "ACCEPT" ? "Kendaraan dinyatakan layak." : "Banding kelayakan dikirim.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title="Periksa Kendaraan" submitLabel="Simpan hasil" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <SelectField label="Hasil pemeriksaan" {...register("decision")}>
        <option value="ACCEPT">Kendaraan layak dipakai</option>
        <option value="APPEAL">Ajukan banding kelayakan</option>
      </SelectField>
      <TextAreaField label="Alasan (wajib jika banding)" error={errors.reason?.message} {...register("reason")} />
    </FormDialog>
  );
}

const returnSchema = z.object({
  condition_on_return: z.string().trim().min(1, "Kondisi saat dikembalikan wajib diisi."),
  note: z.string().trim(),
});
type ReturnValues = z.infer<typeof returnSchema>;

/** Ketua SK peminjam mengajukan pengembalian (BAST) — petugas aset memeriksanya. */
function ReturnDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const requestReturn = useRequestReturn();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ReturnValues>({ resolver: zodResolver(returnSchema), defaultValues: { condition_on_return: asset.condition, note: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await requestReturn.mutateAsync({ allocation_id: asset.allocation_id!, condition_on_return: v.condition_on_return, note: v.note || null });
      toast.success("Pengembalian diajukan. Petugas aset akan memeriksa kondisinya.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title={`Kembalikan ${asset.name}`} submitLabel="Ajukan pengembalian" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <TextField label="Kondisi saat dikembalikan" error={errors.condition_on_return?.message} {...register("condition_on_return")} />
      <TextAreaField label="Catatan (opsional)" {...register("note")} />
    </FormDialog>
  );
}

const verifySchema = z
  .object({ decision: z.enum(["ACCEPT", "REJECT"]), note: z.string().trim() })
  .refine((v) => v.decision === "ACCEPT" || v.note.length > 0, { path: ["note"], message: "Alasan penolakan wajib diisi." });
type VerifyValues = z.infer<typeof verifySchema>;

/** Petugas aset: terima → aset tersedia lagi; tolak → kembali ke tim untuk diperbaiki (R9, tanpa jalan buntu). */
function VerifyReturnDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const verify = useVerifyReturn();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<VerifyValues>({ resolver: zodResolver(verifySchema), defaultValues: { decision: "ACCEPT", note: "" } });
  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    try {
      await verify.mutateAsync({ return_id: asset.pending_return_id!, is_accepted: v.decision === "ACCEPT", note: v.note || null });
      toast.success(v.decision === "ACCEPT" ? "Pengembalian diterima. Aset tersedia lagi." : "Pengembalian ditolak. Aset kembali ke tim.");
      onClose();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  });
  return (
    <FormDialog title={`Periksa pengembalian ${asset.name}`} submitLabel="Simpan hasil" submitting={isSubmitting} formError={formError} onClose={onClose} onSubmit={onSubmit}>
      <p className="mb-3 text-sm text-mist">
        Diajukan {asset.return_requested_by_name ?? "ketua tim"} · kondisi {asset.return_condition}
        {asset.return_note ? ` — ${asset.return_note}` : ""}
      </p>
      <SelectField label="Hasil pemeriksaan" {...register("decision")}>
        <option value="ACCEPT">Terima — aset tersedia lagi</option>
        <option value="REJECT">Tolak — kembali ke tim untuk diperbaiki</option>
      </SelectField>
      <TextAreaField label="Catatan (wajib jika ditolak)" error={errors.note?.message} {...register("note")} />
    </FormDialog>
  );
}

/** Unduh BAST (GET /assets/returns/{id}/pdf, blob). */
async function downloadBast(asset: Asset, item: AssetReturnItem) {
  try {
    const res = await api.get<Blob>(`/assets/returns/${item.id}/pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `BAST-${asset.code}-${item.plan_number ?? ""}.pdf`.replace(/\//g, "-");
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    toast.error(err instanceof ApiError && err.status === 503 ? "Pembuatan PDF sedang tidak tersedia. Coba lagi nanti atau hubungi admin." : errorMessage(err));
  }
}

/** Riwayat pengembalian + berita acara serah terima (P6-4). */
function ReturnHistoryDialog({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const history = useAssetReturns(asset.id);
  return (
    <VmsDialog
      open
      title={`Riwayat pengembalian ${asset.name}`}
      onClose={onClose}
      footer={
        <Button variant="outline" onClick={onClose}>
          Tutup
        </Button>
      }
    >
      {history.isPending && <p className="text-sm text-mist">Memuat…</p>}
      {history.isError && <p className="text-sm text-danger">Riwayat tidak dapat dimuat.</p>}
      {history.data?.length === 0 && <p className="text-sm text-mist">Belum pernah dikembalikan.</p>}
      <ul className="divide-y divide-line text-sm">
        {history.data?.map((r) => (
          <li key={r.id} className="flex flex-col gap-2 py-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="font-medium">
                Rencana Kerja {r.plan_number} ·{" "}
                {r.verified_at ? (r.is_accepted ? "Diterima" : "Ditolak") : "Menunggu pemeriksaan"}
              </p>
              <p className="text-mist">
                {r.requested_by_name} · {formatDateTime(r.requested_at)} · kondisi {r.condition_on_return ?? "-"}
                {r.verified_by_name && ` · diperiksa ${r.verified_by_name}`}
              </p>
            </div>
            {r.verified_at && (
              <Button size="sm" variant="outline" onClick={() => downloadBast(asset, r)}>
                Unduh BAST
              </Button>
            )}
          </li>
        ))}
      </ul>
    </VmsDialog>
  );
}
