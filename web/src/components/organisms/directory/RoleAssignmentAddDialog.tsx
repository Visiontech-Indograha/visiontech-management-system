import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { SelectField } from "@/components/molecules/Field";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { TextBlock } from "@/components/molecules/TextBlock";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { useIdempotencyKey } from "@/lib/idempotency";
import { allowedExtraRoles, EXTRA_ROLE_LABEL, needsOffice, roleAddBlocker, type ExtraRole } from "@/lib/roleAssignments";
import { useOffices } from "@/services/employeeService";
import { useAddRoleAssignment } from "@/services/roleAssignmentService";
import { useSession } from "@/stores/sessionStore";

interface Values {
  role: string;
  office_id: string;
}

/** Dialog "Tambah peran": HR/Finance wajib pilih kantor, OM otomatis semua kantor. Kombinasi terlarang ditolak di layar. */
export function RoleAssignmentAddDialog({ userId, primaryRole, held, scopes, extraCount, isSelf, onClose }: {
  userId: string;
  primaryRole?: string | null;
  held: string[];
  scopes?: { role: string; office_id?: string | null }[];
  extraCount: number;
  isSelf: boolean;
  onClose: () => void;
}) {
  const offices = useOffices();
  const roles = allowedExtraRoles(useSession().me?.permissions);
  const mutation = useAddRoleAssignment(userId);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<Values>({ defaultValues: { role: "", office_id: "" } });
  const values = useWatch({ control });
  const idem = useIdempotencyKey(JSON.stringify(values));
  const role = values.role ?? "";
  const blocker = role ? roleAddBlocker({ role, primaryRole, held, scopes, officeId: values.office_id, extraCount, isSelf }) : null;

  const onSubmit = async (v: Values) => {
    setFormError(null);
    if (!v.role) return setError("role", { message: "Pilih peran." });
    const stop = roleAddBlocker({ role: v.role, primaryRole, held, scopes, officeId: v.office_id, extraCount, isSelf });
    if (stop) return setFormError(stop);
    if (needsOffice(v.role) && !v.office_id) return setError("office_id", { message: "Pilih kantor." });
    try {
      await mutation.mutateAsync({
        body: { role: v.role as ExtraRole, office_id: needsOffice(v.role) ? v.office_id : null },
        key: idem.key,
      });
      idem.renew();
      toast.success("Peran tambahan berhasil disimpan.");
      onClose();
    } catch (err) {
      if (applyFieldErrors(err, setError, ["role", "office_id"])) {
        setFormError("Periksa kolom yang ditandai.");
        return;
      }
      setFormError(errorMessage(err, "Peran belum dapat ditambahkan. Coba lagi."));
    }
  };

  return (
    <VmsDialog
      dirty={isDirty}
      open
      title="Tambah peran"
      onClose={onClose}
      footer={
        <DialogActions
          onCancel={onClose}
          busy={isSubmitting || mutation.isPending}
          submitDisabled={!!blocker}
          formId="role-assignment-form"
          submitLabel="Simpan peran"
          busyLabel="Menyimpan..."
        />
      }
    >
      <FormBlock id="role-assignment-form" onSubmit={handleSubmit(onSubmit)}>
        <FormErrorText message={blocker} />
        <FormErrorText message={formError} />
        <SelectField label="Peran tambahan" error={errors.role?.message} {...register("role", { required: "Pilih peran." })}>
          <ControlOption value="">Pilih peran</ControlOption>
          {roles.map((r) => (
            <ControlOption key={r} value={r}>{EXTRA_ROLE_LABEL[r]}</ControlOption>
          ))}
        </SelectField>
        {needsOffice(role) && (
          <SelectField label="Kantor" error={errors.office_id?.message} {...register("office_id")}>
            <ControlOption value="">Pilih kantor</ControlOption>
            {(offices.data ?? []).map((o) => (
              <ControlOption key={o.id} value={o.id}>{o.name}</ControlOption>
            ))}
          </SelectField>
        )}
        {needsOffice(role) && <TextBlock className="text-sm text-mist">Berlaku hanya untuk kantor yang dipilih.</TextBlock>}
        {role === "OPERATIONAL_MANAGER" && <TextBlock className="text-sm text-mist">Berlaku untuk semua kantor.</TextBlock>}
      </FormBlock>
    </VmsDialog>
  );
}
