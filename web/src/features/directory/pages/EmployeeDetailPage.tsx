import { zodResolver } from "@hookform/resolvers/zod";
import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useParams } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { useSession } from "@/app/session";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import { SelectField, TextField } from "@/components/molecules/Field";
import { PageHeader } from "@/components/molecules/PageHeader";
import { Skeleton } from "@/components/atoms/Skeleton";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ApiError } from "@/lib/apiClient";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { useArchiveEmployee, useEmployee, useRestoreEmployee, useUnits, useUpdateEmployee, type Employee, type EmployeeUpdate } from "../employeeService";
import { AssignmentHistory, PromoteDialog } from "../components/AssignmentHistory";
import { OffboardDialog } from "../components/EmployeeLifecycleDialogs";
import { AccountCard } from "../components/AccountCard";
import { DocumentsPanel } from "../components/DocumentsPanel";

const Row = ({ label, children }: { label: string; children: ReactNode }) => (
  <div className="flex justify-between gap-4 border-b border-line py-2 last:border-0">
    <dt className="text-mist">{label}</dt>
    <dd className="text-right font-medium">{children ?? "-"}</dd>
  </div>
);

export function EmployeeDetailPage() {
  const { id = "" } = useParams();
  const fromList = (useLocation().state as { employee?: Employee } | null)?.employee;
  const { me } = useSession();
  const employee = useEmployee(id, fromList?.id === id ? fromList : undefined);
  const [editing, setEditing] = useState(false);
  const [promoting, setPromoting] = useState(false);
  const [offboarding, setOffboarding] = useState(false);
  const units = useUnits();
  const canEdit = !!me?.permissions.includes("manage:users");
  const canManageDocs = !!me?.permissions.includes("manage:employee_documents");
  // M2-01 (prototipe privateAccess): data kontak pribadi hanya untuk HR/admin & pemiliknya — server pun menyaringnya.
  const canSeePrivate = canManageDocs || me?.employee_id === id;
  const e = employee.data;

  if (employee.isError)
    return (
      <div className="mt-16 text-center">
        <p className="mb-3 text-danger">{employee.error.message}</p>
        <Link to="/directory" className="font-semibold text-lens hover:underline">
          Kembali ke Direktori
        </Link>
      </div>
    );

  if (!e)
    return (
      <div aria-hidden className="max-w-xl space-y-3">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-40 w-full" />
      </div>
    );

  return (
    <>
      <PageHeader
        title={e.full_name}
        action={
          canEdit && (
            <div className="flex flex-wrap gap-2">
              {e.is_active && (
                <Button variant="outline" onClick={() => setPromoting(true)}>
                  Mutasi / promosi
                </Button>
              )}
              {e.is_active && (
                <Button variant="outline" onClick={() => setOffboarding(true)}>
                  Offboarding
                </Button>
              )}
              <Button variant="outline" onClick={() => setEditing(true)}>
                Ubah profil
              </Button>
            </div>
          )
        }
      />
      <div className="mb-8 max-w-xl rounded-panel border border-line bg-surface shadow-card px-5 py-2">
        <dl className="text-sm">
          <Row label="No. karyawan">{e.employee_no}</Row>
          <Row label="Jabatan">{e.position}</Row>
          <Row label="Unit">{units.data?.find((u) => u.id === e.unit_id)?.name ?? null}</Row>
          <Row label="Akun">{e.is_active ? <Badge tone="success">Aktif</Badge> : <Badge>Nonaktif</Badge>}</Row>
          <Row label="Tanggal bergabung">{formatDate(e.join_date)}</Row>
          <Row label="Absen lewat">{ATTENDANCE_MODE_LABEL[e.attendance_mode ?? "FIELD"]}</Row>
          {canSeePrivate && (
            <>
              <Row label="Email">{e.email}</Row>
              <Row label="No. telepon">{e.phone}</Row>
              <Row label="Tanggal lahir">{e.birth_date ? formatDate(e.birth_date) : null}</Row>
              <Row label="Alamat">{e.address}</Row>
              <Row label="Kontak darurat">{e.emergency_contact}</Row>
            </>
          )}
          {e.offboarded_at && (
            <Row label="Keluar">
              {formatDate(e.offboarded_at)} – {e.offboarding_reason ?? "-"}
            </Row>
          )}
        </dl>
        {!canSeePrivate && (
          <p className="border-t border-line py-3 text-caption text-mist">
            Data kontak pribadi dan dokumen identitas hanya terlihat oleh pemilik serta HR.
          </p>
        )}
      </div>
      {canEdit && <AccountCard employee={e} />}
      <AssignmentHistory employee={e} />
      {canEdit && !e.is_active && <ArchivePanel employee={e} />}
      {canManageDocs && <DocumentsPanel employeeId={e.id} canManage canVerify={!!me?.permissions.includes("verify:documents")} />}
      {editing && <ProfileDialog employee={e} onClose={() => setEditing(false)} />}
      {promoting && <PromoteDialog employee={e} onClose={() => setPromoting(false)} />}
      {offboarding && <OffboardDialog employee={e} onClose={() => setOffboarding(false)} />}
    </>
  );
}

const optional = z.string().trim();
const profileSchema = z.object({
  full_name: z.string().trim().min(1, "Nama wajib diisi."),
  email: z.union([z.literal(""), z.email("Format email tidak valid.")]),
  phone: optional.max(30, "No. telepon maksimal 30 karakter."),
  birth_date: optional,
  address: optional,
  emergency_contact: optional,
  attendance_mode: z.enum(["FIELD", "OFFICE"], "Pilih cara absen."),
});
type ProfileValues = z.infer<typeof profileSchema>;
const FIELDS = ["full_name", "email", "phone", "birth_date", "address", "emergency_contact", "attendance_mode"] as const;
/** FIELD = pekerja lapangan (absen di aplikasi HP), OFFICE = pekerja kantor (absen di web). */
const ATTENDANCE_MODE_LABEL: Record<string, string> = {
  FIELD: "Aplikasi HP (pekerja lapangan)",
  OFFICE: "Web (pekerja kantor)",
};

function ProfileDialog({ employee, onClose }: { employee: Employee; onClose: () => void }) {
  const update = useUpdateEmployee(employee.id);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: employee.full_name,
      email: employee.email ?? "",
      phone: employee.phone ?? "",
      birth_date: employee.birth_date ?? "",
      address: employee.address ?? "",
      emergency_contact: employee.emergency_contact ?? "",
      attendance_mode: employee.attendance_mode ?? "FIELD",
    },
  });

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null);
    const body: EmployeeUpdate = {
      full_name: v.full_name,
      email: v.email || null,
      phone: v.phone || null,
      birth_date: v.birth_date || null,
      address: v.address || null,
      emergency_contact: v.emergency_contact || null,
      attendance_mode: v.attendance_mode,
    };
    try {
      await update.mutateAsync(body);
      toast.success("Profil disimpan.");
      onClose();
    } catch (err) {
      const fields = err instanceof ApiError ? ((err.details.fields ?? {}) as Record<string, string>) : {};
      const known = FIELDS.filter((f) => fields[f]);
      if (known.length) known.forEach((f) => setError(f, { message: fields[f] }));
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  });

  return (
    <VmsDialog
      open
      title="Ubah profil"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" form="profile-form" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : "Simpan"}
          </Button>
        </>
      }
    >
      <form id="profile-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <TextField label="Nama lengkap" error={errors.full_name?.message} {...register("full_name")} />
        <TextField label="Email" type="email" error={errors.email?.message} {...register("email")} />
        <TextField label="No. telepon" error={errors.phone?.message} {...register("phone")} />
        <TextField label="Tanggal lahir" type="date" error={errors.birth_date?.message} {...register("birth_date")} />
        <TextField label="Alamat" error={errors.address?.message} {...register("address")} />
        <TextField label="Kontak darurat" error={errors.emergency_contact?.message} {...register("emergency_contact")} />
        <SelectField label="Absen lewat" error={errors.attendance_mode?.message} {...register("attendance_mode")}>
          <option value="FIELD">{ATTENDANCE_MODE_LABEL.FIELD}</option>
          <option value="OFFICE">{ATTENDANCE_MODE_LABEL.OFFICE}</option>
        </SelectField>
      </form>
    </VmsDialog>
  );
}

/**
 * Hapus (arsip) karyawan yang sudah di-offboard dan pulihkan kembali (V-29). API tidak menampilkan
 * karyawan terhapus di daftar, jadi pemulihan tersedia di halaman ini selama detailnya masih terbuka.
 */
function ArchivePanel({ employee }: { employee: Employee }) {
  const archive = useArchiveEmployee(employee.id);
  const restore = useRestoreEmployee(employee.id);
  const [archived, setArchived] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const busy = archive.isPending || restore.isPending;

  const doArchive = async () => {
    setError(null);
    try {
      await archive.mutateAsync();
      setArchived(true);
      toast.success("Karyawan dihapus dari direktori.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setConfirming(false);
    }
  };
  const doRestore = async () => {
    setError(null);
    try {
      await restore.mutateAsync();
      setArchived(false);
      toast.success("Karyawan dipulihkan sebagai nonaktif.");
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <section aria-label="Hapus karyawan" className="mb-8 max-w-xl rounded-panel border border-line bg-surface shadow-card p-4">
      {error && (
        <p role="alert" className="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}
      {archived ? (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <p className="text-sm">Karyawan ini sudah dihapus dan tidak tampil di Direktori.</p>
          <Button variant="outline" onClick={doRestore} disabled={busy}>
            Pulihkan karyawan
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <p className="text-sm text-mist">Karyawan nonaktif dapat dihapus dari Direktori. Data historis tetap tersimpan.</p>
          <Button variant="outline" onClick={() => setConfirming(true)} disabled={busy}>
            Hapus karyawan
          </Button>
        </div>
      )}
      <VmsDialog
        open={confirming}
        title="Hapus karyawan?"
        onClose={() => setConfirming(false)}
        footer={
          <>
            <Button variant="outline" onClick={() => setConfirming(false)} disabled={busy}>
              Batal
            </Button>
            <Button onClick={doArchive} disabled={busy}>
              Ya, hapus
            </Button>
          </>
        }
      >
        <p className="text-sm">
          {employee.full_name} akan disembunyikan dari Direktori. Riwayat rencana kerja, absensi, dan dokumennya tidak dihapus.
        </p>
      </VmsDialog>
    </section>
  );
}
