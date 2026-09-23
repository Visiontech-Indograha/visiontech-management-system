import { useState } from "react";
import toast from "react-hot-toast";
import { Link, useParams } from "react-router-dom";
import { useSession } from "@/app/session";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { SelectField, TextField } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { EMPLOYMENT_LABEL, ROLE_LABEL } from "@/lib/types";
import { useEmployee, useUpdateProfile, type Employee } from "./api";
import { CompletenessBadge } from "./badges";
import { DocumentsPanel } from "./DocumentsPanel";

const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div className="flex justify-between gap-4 border-b border-line py-2 last:border-0">
    <dt className="text-mist">{label}</dt>
    <dd className="text-right font-medium">{children ?? "-"}</dd>
  </div>
);

export function EmployeeDetailPage() {
  const { id = "" } = useParams();
  const { me, can } = useSession();
  const employee = useEmployee(id);
  const [editing, setEditing] = useState(false);
  const canEdit = !!me?.manage_permissions.includes("employee:profile_update");
  const seesDocs = can("employee_document:manage") || me?.id === id;
  const e = employee.data;

  if (employee.isError)
    return (
      <div className="mt-16 text-center">
        <p className="mb-3 text-danger">Karyawan tidak ditemukan.</p>
        <Link to="/directory" className="font-semibold text-lens hover:underline">
          Kembali ke Direktori
        </Link>
      </div>
    );

  return (
    <>
      <PageHeader
        title={e?.full_name ?? "Karyawan"}
        action={canEdit && e && <Button variant="secondary" onClick={() => setEditing(true)}>Ubah profil</Button>}
      />
      {e && (
        <div className="mb-8 max-w-xl rounded-panel border border-line bg-surface px-5 py-2">
          <dl className="text-sm">
            <Row label="Username">{e.username}</Row>
            <Row label="Role">{ROLE_LABEL[e.user_type ?? e.role]}</Row>
            <Row label="Status kerja">{e.employment_type ? EMPLOYMENT_LABEL[e.employment_type] : "-"}</Row>
            <Row label="Akun">{e.is_active ? <Badge tone="success">Aktif</Badge> : <Badge>Nonaktif</Badge>}</Row>
            <Row label="No. karyawan">{e.employee_no}</Row>
            <Row label="No. telepon">{e.phone}</Row>
            <Row label="Tanggal bergabung">{e.join_date ? formatDate(e.join_date) : null}</Row>
            {e.employment_type === "CONTRACT" && (
              <Row label="Kontrak">
                {e.contract_start ? formatDate(e.contract_start) : "-"} – {e.contract_end ? formatDate(e.contract_end) : "-"}
              </Row>
            )}
            {e.documents_status && (
              <Row label="Kelengkapan berkas">
                <CompletenessBadge status={e.documents_status} missing={e.documents_missing?.length} />
              </Row>
            )}
          </dl>
        </div>
      )}
      {e?.documents_missing && e.documents_missing.length > 0 && (
        <p role="status" className="mb-4 rounded-control bg-warning-soft px-3 py-2 text-sm text-warning">
          Berkas wajib yang kurang: {e.documents_missing.map((m) => m.name).join(", ")}.
        </p>
      )}
      {seesDocs && <DocumentsPanel userId={id} canManage={can("employee_document:manage")} />}
      {e && editing && <ProfileDialog employee={e} onClose={() => setEditing(false)} />}
    </>
  );
}

function ProfileDialog({ employee, onClose }: { employee: Employee; onClose: () => void }) {
  const update = useUpdateProfile(employee.id);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const submit = async (ev: React.FormEvent<HTMLFormElement>) => {
    ev.preventDefault();
    const f = new FormData(ev.currentTarget);
    const val = (k: string) => String(f.get(k) ?? "").trim() || null;
    setErrors({});
    setFormError(null);
    try {
      await update.mutateAsync({
        employment_type: f.get("employment_type"),
        phone: val("phone"),
        employee_no: val("employee_no"),
        join_date: val("join_date"),
        contract_start: val("contract_start"),
        contract_end: val("contract_end"),
      });
      toast.success("Profil disimpan.");
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details.fields) setErrors(err.details.fields as Record<string, string>);
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };

  return (
    <Dialog
      open
      title="Ubah profil"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Batal
          </Button>
          <Button type="submit" form="profile-form" disabled={update.isPending}>
            Simpan
          </Button>
        </>
      }
    >
      <form id="profile-form" onSubmit={submit} noValidate>
        {formError && (
          <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <SelectField name="employment_type" label="Status kerja" defaultValue={employee.employment_type ?? "CONTRACT"} error={errors.employment_type}>
          <option value="PERMANENT">Tetap</option>
          <option value="CONTRACT">Kontrak</option>
        </SelectField>
        <TextField name="employee_no" label="No. karyawan" defaultValue={employee.employee_no ?? ""} error={errors.employee_no} />
        <TextField name="phone" label="No. telepon" defaultValue={employee.phone ?? ""} error={errors.phone} />
        <TextField name="join_date" label="Tanggal bergabung" type="date" defaultValue={employee.join_date ?? ""} error={errors.join_date} />
        <TextField name="contract_start" label="Awal kontrak" type="date" defaultValue={employee.contract_start ?? ""} error={errors.contract_start} />
        <TextField name="contract_end" label="Akhir kontrak" type="date" defaultValue={employee.contract_end ?? ""} error={errors.contract_end} />
      </form>
    </Dialog>
  );
}
