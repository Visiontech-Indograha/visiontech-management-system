import { Copy } from "lucide-react";
import { useState } from "react";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/VmsDialog";
import { SelectField, TextField } from "@/components/ui/Field";
import { ApiError } from "@/lib/api";
import { EMPLOYMENT_LABEL, ROLE_LABEL, type UserCreate, type UserOut, type UserUpdate } from "@/lib/types";
import {
  useCreateUser,
  useDeactivateUser,
  useOpenItems,
  useResetPassword,
  useUpdateUser,
} from "./api";

type FieldErrors = Record<string, string>;

function fieldErrors(e: unknown): { fields: FieldErrors; message: string } {
  if (e instanceof ApiError) return { fields: (e.details.fields ?? {}) as FieldErrors, message: e.message };
  return { fields: {}, message: "Terjadi kesalahan. Coba lagi." };
}

function ErrorNote({ message }: { message: string | null }) {
  return message ? (
    <p role="alert" className="mb-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
      {message}
    </p>
  ) : null;
}

/** Password sementara ditampilkan sekali (FR-USR-01, FR-USR-04). */
export function TemporaryPasswordDialog({
  username,
  password,
  onClose,
}: {
  username: string;
  password: string | null;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={password !== null}
      title="Password sementara"
      onClose={onClose}
      footer={<Button onClick={onClose}>Selesai</Button>}
    >
      <p className="mb-3">
        Berikan password ini kepada <strong>{username}</strong>. Password hanya ditampilkan sekali dan wajib diganti saat
        login pertama.
      </p>
      <div className="flex items-center justify-between rounded-control border border-line bg-paper px-3 py-2">
        <code className="text-base font-semibold tracking-wider" data-testid="temp-password">
          {password}
        </code>
        <button
          type="button"
          aria-label="Salin password"
          className="rounded-control p-1 text-mist hover:bg-hover"
          onClick={() => {
            void navigator.clipboard?.writeText(password ?? "");
            toast.success("Password disalin.");
          }}
        >
          <Copy size={16} />
        </button>
      </div>
    </Dialog>
  );
}

export function CreateUserDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (username: string, tempPassword: string) => void;
}) {
  const create = useCreateUser();
  const [role, setRole] = useState("user");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const text = (k: string) => (String(f.get(k) ?? "").trim() || undefined);
    const payload: UserCreate = {
      username: String(f.get("username") ?? "").trim(),
      full_name: String(f.get("full_name") ?? "").trim(),
      role: role as UserCreate["role"],
      user_type: role === "user" ? (text("user_type") as UserCreate["user_type"]) : undefined,
      employment_type: role === "super_admin" ? undefined : (text("employment_type") as UserCreate["employment_type"]),
      phone: text("phone"),
      employee_no: text("employee_no"),
      join_date: text("join_date"),
      description: role === "team_leader" ? text("description") : undefined,
    };
    setErrors({});
    setFormError(null);
    try {
      const created = await create.mutateAsync(payload);
      onCreated(created.username, created.temporary_password);
      onClose();
    } catch (err) {
      const { fields, message } = fieldErrors(err);
      setErrors(fields);
      setFormError(Object.keys(fields).length ? null : message);
    }
  };

  return (
    <Dialog
      open={open}
      title="Tambah user"
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Batal
          </Button>
          <Button type="submit" form="create-user-form" disabled={create.isPending}>
            {create.isPending ? "Menyimpan..." : "Buat user"}
          </Button>
        </>
      }
    >
      <form id="create-user-form" onSubmit={submit} noValidate>
        <ErrorNote message={formError} />
        <TextField
          name="username"
          label="Username"
          hint="Huruf kecil, angka, titik, garis bawah (3–30 karakter)."
          autoCapitalize="none"
          error={errors.username}
        />
        <TextField name="full_name" label="Nama lengkap" error={errors.full_name} />
        <SelectField label="Role" value={role} onChange={(e) => setRole(e.target.value)} error={errors.role}>
          {Object.entries(ROLE_LABEL)
            .filter(([k]) => !["WTL", "DRIVER"].includes(k))
            .map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
        </SelectField>
        {role === "user" && (
          <SelectField name="user_type" label="Tipe user" error={errors.user_type} defaultValue="WTL">
            <option value="WTL">WTL</option>
            <option value="DRIVER">Driver</option>
          </SelectField>
        )}
        {role !== "super_admin" && (
          <SelectField
            name="employment_type"
            label="Status kerja"
            error={errors.employment_type}
            defaultValue="CONTRACT"
          >
            {Object.entries(EMPLOYMENT_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </SelectField>
        )}
        <TextField name="phone" label="No. telepon" inputMode="tel" error={errors.phone} />
        <TextField name="employee_no" label="No. karyawan" error={errors.employee_no} />
        <TextField name="join_date" label="Tanggal bergabung" type="date" error={errors.join_date} />
        {role === "team_leader" && (
          <TextField name="description" label="Deskripsi" error={errors.description} />
        )}
      </form>
    </Dialog>
  );
}

export function EditUserDialog({ user, onClose }: { user: UserOut | null; onClose: () => void }) {
  const update = useUpdateUser();
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [type, setType] = useState<string | null>(null);
  if (!user) return null;

  const effectiveRole = role ?? user.role;
  const roleChanged = role !== null && role !== user.role;
  const canChangeRole = user.role !== "super_admin";

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const data: Record<string, unknown> = {
      full_name: String(f.get("full_name") ?? "").trim(),
      phone: String(f.get("phone") ?? "").trim() || null,
      employee_no: String(f.get("employee_no") ?? "").trim() || null,
    };
    if (user.role !== "super_admin") data.employment_type = f.get("employment_type");
    if (roleChanged || type !== null) {
      data.role = effectiveRole;
      data.user_type = effectiveRole === "user" ? (type ?? user.user_type ?? "WTL") : null;
      data.confirm_role_change = f.get("confirm_role_change") === "on";
    }
    setErrors({});
    setFormError(null);
    try {
      await update.mutateAsync({ id: user.id, data: data as unknown as UserUpdate });
      toast.success("Perubahan disimpan.");
      onClose();
    } catch (err) {
      const { fields, message } = fieldErrors(err);
      setErrors(fields);
      setFormError(Object.keys(fields).length ? null : message);
    }
  };

  return (
    <Dialog
      open
      title={`Ubah ${user.full_name}`}
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Batal
          </Button>
          <Button type="submit" form="edit-user-form" disabled={update.isPending}>
            Simpan
          </Button>
        </>
      }
    >
      <form id="edit-user-form" onSubmit={submit} noValidate>
        <ErrorNote message={formError} />
        <TextField name="full_name" label="Nama lengkap" defaultValue={user.full_name} error={errors.full_name} />
        {user.role !== "super_admin" && (
          <SelectField
            name="employment_type"
            label="Status kerja"
            defaultValue={user.employment_type ?? "CONTRACT"}
            error={errors.employment_type}
          >
            {Object.entries(EMPLOYMENT_LABEL).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </SelectField>
        )}
        <TextField name="phone" label="No. telepon" defaultValue={user.phone ?? ""} error={errors.phone} />
        <TextField
          name="employee_no"
          label="No. karyawan"
          defaultValue={user.employee_no ?? ""}
          error={errors.employee_no}
        />
        {canChangeRole && (
          <>
            <SelectField
              label="Role"
              value={effectiveRole}
              onChange={(e) => setRole(e.target.value)}
              error={errors.role}
            >
              {["admin", "team_leader", "finance", "hes", "user"].map((v) => (
                <option key={v} value={v}>
                  {ROLE_LABEL[v]}
                </option>
              ))}
            </SelectField>
            {effectiveRole === "user" && (
              <SelectField
                label="Tipe user"
                value={type ?? user.user_type ?? "WTL"}
                onChange={(e) => setType(e.target.value)}
                error={errors.user_type}
              >
                <option value="WTL">WTL</option>
                <option value="DRIVER">Driver</option>
              </SelectField>
            )}
            {(roleChanged || type !== null) && (
              <label className="mb-4 flex items-start gap-2 text-sm">
                <input type="checkbox" name="confirm_role_change" className="mt-1" />
                <span>
                  Saya mengonfirmasi perubahan role. Semua sesi user ini akan berakhir.
                  {errors.confirm_role_change && (
                    <span role="alert" className="block text-danger">
                      {errors.confirm_role_change}
                    </span>
                  )}
                  {errors.role && <span className="block text-danger">{errors.role}</span>}
                </span>
              </label>
            )}
          </>
        )}
      </form>
    </Dialog>
  );
}

export function ResetPasswordDialog({
  user,
  onClose,
  onDone,
}: {
  user: UserOut | null;
  onClose: () => void;
  onDone: (username: string, tempPassword: string) => void;
}) {
  const reset = useResetPassword();
  if (!user) return null;
  return (
    <Dialog
      open
      title={`Reset password ${user.full_name}?`}
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Batal
          </Button>
          <Button
            disabled={reset.isPending}
            onClick={async () => {
              try {
                const r = await reset.mutateAsync(user.id);
                onDone(user.username, r.temporary_password);
                onClose();
              } catch (e) {
                toast.error(fieldErrors(e).message);
              }
            }}
          >
            Reset password
          </Button>
        </>
      }
    >
      Password sementara baru dibuat dan semua sesi {user.username} berakhir.
    </Dialog>
  );
}

export function DeactivateDialog({ user, onClose }: { user: UserOut | null; onClose: () => void }) {
  const deactivate = useDeactivateUser();
  const openItems = useOpenItems(user?.id ?? null);
  const [error, setError] = useState<string | null>(null);
  if (!user) return null;
  const items = openItems.data;
  const hasOpen = !!items && (items.vehicle_loans.length > 0 || items.issuances.length > 0);

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setError(null);
    try {
      await deactivate.mutateAsync({
        id: user.id,
        reason: String(f.get("reason") ?? "").trim(),
        resign_date: String(f.get("resign_date") ?? "") || undefined,
      });
      toast.success("Akun dinonaktifkan.");
      onClose();
    } catch (err) {
      const { fields, message } = fieldErrors(err);
      setError(fields.reason ?? message);
    }
  };

  return (
    <Dialog
      open
      title={`Nonaktifkan ${user.full_name}?`}
      onClose={onClose}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Batal
          </Button>
          <Button variant="destructive" type="submit" form="deactivate-form" disabled={deactivate.isPending}>
            Nonaktifkan
          </Button>
        </>
      }
    >
      {hasOpen && (
        <p role="status" className="mb-4 rounded-control bg-warning-soft px-3 py-2 text-sm text-warning">
          User ini masih memegang {items!.vehicle_loans.length} kendaraan dan {items!.issuances.length} barang/tool
          yang belum kembali.
        </p>
      )}
      <p className="mb-4 text-sm text-mist">
        User tidak dapat login dan semua sesi berakhir. Data dan riwayat tetap tersimpan.
      </p>
      <form id="deactivate-form" onSubmit={submit} noValidate>
        <ErrorNote message={error} />
        <TextField name="reason" label="Alasan" />
        <TextField name="resign_date" label="Tanggal resign (opsional)" type="date" />
      </form>
    </Dialog>
  );
}
