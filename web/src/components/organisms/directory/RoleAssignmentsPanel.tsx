import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { QueryState } from "@/components/molecules/QueryState";
import { SectionTitle } from "@/components/molecules/SectionTitle";
import { TextBlock } from "@/components/molecules/TextBlock";
import { ConfirmDialog } from "@/components/organisms/ConfirmDialog";
import { RoleAssignmentAddDialog } from "@/components/organisms/directory/RoleAssignmentAddDialog";
import { errorMessage } from "@/lib/errors";
import { roleName } from "@/lib/roleAssignments";
import { useAccount, type Employee } from "@/services/employeeService";
import {
  useRevokeRoleAssignment,
  useRoleAssignments,
  type RoleAssignment,
} from "@/services/roleAssignmentService";
import { useSession } from "@/stores/sessionStore";

/**
 * Bagian "Peran tambahan dan kantor": hanya untuk pemegang izin manage:role_assignments (Super Admin).
 * Tanpa izin, bagian ini tidak tampil sama sekali (API tetap memeriksa).
 */
export function RoleAssignmentsPanel({ employee }: { employee: Employee }) {
  const me = useSession().me;
  const allowed = !!me?.permissions.includes("manage:role_assignments");
  if (!allowed) return null;
  return <PanelBody employee={employee} myUserId={me?.user_id} />;
}

function PanelBody({ employee, myUserId }: { employee: Employee; myUserId?: string }) {
  const account = useAccount(employee.employee_id);
  const userId = account.data?.exists ? (account.data.user_id ?? null) : null;
  const list = useRoleAssignments(userId);
  const revoke = useRevokeRoleAssignment(userId ?? "");
  const [adding, setAdding] = useState(false);
  const [target, setTarget] = useState<RoleAssignment | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rows = list.data ?? [];
  const extras = rows.filter((r) => r.source !== "PRIMARY");
  const primaryRole = account.data?.system_role;
  const held = [...(primaryRole ? [primaryRole] : []), ...extras.map((r) => r.role)];

  const doRevoke = async () => {
    if (!target) return;
    setError(null);
    try {
      await revoke.mutateAsync(target.assignment_id);
      toast.success("Peran tambahan dicabut.");
      setTarget(null);
    } catch (err) {
      setTarget(null);
      setError(errorMessage(err, "Peran belum dapat dicabut. Coba lagi."));
    }
  };

  return (
    <section aria-label="Peran tambahan dan kantor" className="mb-8 max-w-xl">
      <SectionTitle>Peran tambahan dan kantor</SectionTitle>
      <div className="rounded-panel border border-line bg-surface px-5 py-4 text-sm shadow-card">
        <QueryState query={account} errorText="Akun tidak dapat dimuat.">
          {userId === null ? (
            <TextBlock className="text-mist">Karyawan ini belum punya akun login, jadi belum bisa diberi peran tambahan.</TextBlock>
          ) : (
            <QueryState
              query={list}
              errorText="Daftar peran tidak dapat dimuat."
              empty={rows.length === 0}
              emptyText="Belum ada peran tambahan."
              emptyAction={
                <ActionButton onClick={() => setAdding(true)} className="min-h-11">Tambah peran</ActionButton>
              }
            >
              <FormErrorText message={error} className="mb-3" />
              <div role="list" className="mb-3 divide-y divide-line">
                {rows.map((r) => (
                  <div role="listitem" key={r.assignment_id} className="flex items-center justify-between gap-3 py-2">
                    <TextBlock>
                      {roleName(r.role)} · {r.office_name ?? "Semua kantor"}
                      {r.source === "PRIMARY" ? " (peran utama)" : ""}
                    </TextBlock>
                    {r.source !== "PRIMARY" && (
                      <ActionButton
                        size="sm"
                        variant="outline"
                        className="min-h-11"
                        aria-label={`Cabut ${roleName(r.role)}`}
                        onClick={() => setTarget(r)}
                      >
                        Cabut
                      </ActionButton>
                    )}
                  </div>
                ))}
              </div>
              <ActionButton onClick={() => setAdding(true)} className="min-h-11">Tambah peran</ActionButton>
            </QueryState>
          )}
        </QueryState>
      </div>
      {adding && userId && (
        <RoleAssignmentAddDialog
          userId={userId}
          primaryRole={primaryRole}
          held={held}
          extraCount={extras.length}
          isSelf={!!myUserId && myUserId === userId}
          onClose={() => setAdding(false)}
        />
      )}
      <ConfirmDialog
        open={!!target}
        danger
        title="Cabut peran tambahan?"
        message={target ? `${roleName(target.role)} (${target.office_name ?? "Semua kantor"}) akan dicabut dari akun ini.` : ""}
        confirmLabel="Cabut"
        busy={revoke.isPending}
        onConfirm={() => void doRevoke()}
        onClose={() => setTarget(null)}
      />
    </section>
  );
}
