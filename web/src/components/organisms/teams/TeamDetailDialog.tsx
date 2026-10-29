import { useState } from "react";
import { toast } from "sonner";
import { UserAvatar } from "@/components/organisms/UserAvatar";
import { ActionButton } from "@/components/molecules/ActionButton";
import { ContactLinks } from "@/components/molecules/ContactLinks";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ControlOption } from "@/components/molecules/FormBlock";
import { ImageView } from "@/components/molecules/ImageView";
import { Trash2 } from "@/components/molecules/Glyphs";
import { ListBlock, ListEntry } from "@/components/molecules/ListBlock";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { Pill } from "@/components/molecules/Pill";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { errorMessage } from "@/lib/errors";
import { useEmployees } from "@/services/employeeService";
import { useAddTeamMember, useRemoveTeamMember, useTeam, useTeamLogo, type Team } from "@/services/teamService";

/** Anggota tim + kontak (Telepon/WhatsApp), tambah/keluarkan anggota (karyawan aktif divisi tim). */
export function TeamDetailDialog({ team, onClose }: { team: Team; onClose: () => void }) {
  const detail = useTeam(team.team_id);
  const [q, setQ] = useState("");
  const candidates = useEmployees({ status: "active", page: 1, q: q.trim() || undefined, division_id: team.division_id });
  const add = useAddTeamMember(team.team_id);
  const remove = useRemoveTeamMember(team.team_id);
  const [pick, setPick] = useState("");
  const logo = useTeamLogo(team.team_id, Boolean(team.logo_url));
  const members = detail.data?.members ?? [];
  const inTeam = new Set(members.map((m) => m.employee_id));
  const options = (candidates.data?.items ?? []).filter((e) => !inTeam.has(e.employee_id));

  const run = async (p: Promise<unknown>, ok: string) => {
    try {
      await p;
      toast.success(ok);
      await detail.refetch();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <VmsDialog open title={`Anggota ${team.name}`} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          {logo.data && <ImageView src={logo.data} alt={`Logo ${team.name}`} className="h-12 max-w-40 object-contain" />}
          <TextBlock className="text-sm text-mist">{`${team.division_name ?? "-"} · ${team.office_name ?? "-"}`}</TextBlock>
        </div>
        {detail.isPending && <LoadingBar />}
        <ListBlock className="divide-y divide-line rounded-panel border border-line">
          {members.map((m) => {
            const leader = m.employee_id === team.leader_employee_id;
            return (
              <ListEntry key={m.member_id} className="flex flex-wrap items-center gap-2 p-3">
                <UserAvatar name={m.full_name} fileId={m.photo_file_id} size="sm" />
                <div className="min-w-40 flex-1">
                  <TextBlock className="text-sm font-medium">
                    {m.full_name} {leader && <Pill tone="info">Ketua</Pill>}
                  </TextBlock>
                  <TextBlock className="text-xs text-mist">{`${m.employee_no ?? "-"} · ${m.system_role ?? "-"}`}</TextBlock>
                </div>
                <ContactLinks phone={m.phone_number} name={m.full_name} />
                {!leader && (
                  <ActionButton
                    size="sm"
                    variant="ghost"
                    aria-label={`Keluarkan ${m.full_name}`}
                    disabled={remove.isPending}
                    onClick={() => void run(remove.mutateAsync(m.employee_id), `${m.full_name} dikeluarkan dari tim.`)}
                  >
                    <Trash2 size={16} />
                  </ActionButton>
                )}
              </ListEntry>
            );
          })}
          {!detail.isPending && members.length === 0 && (
            <ListEntry className="p-3 text-sm text-mist">Belum ada anggota.</ListEntry>
          )}
        </ListBlock>
        <div className="flex flex-wrap items-end gap-2">
          <TextField label="Cari karyawan" placeholder="Nama / NIK" value={q} onChange={(e) => setQ(e.target.value)} />
          <SelectField label="Tambah anggota (karyawan divisi ini)" value={pick} onChange={(e) => setPick(e.target.value)}>
            <ControlOption value="">Pilih karyawan</ControlOption>
            {options.map((e) => (
              <ControlOption key={e.employee_id} value={e.employee_id}>{`${e.full_name} (${e.employee_no})`}</ControlOption>
            ))}
          </SelectField>
          <ActionButton
            size="sm"
            disabled={!pick || add.isPending}
            onClick={() => void run(add.mutateAsync(pick), "Anggota ditambahkan.").then(() => setPick(""))}
          >
            Tambah
          </ActionButton>
        </div>
        {!candidates.isPending && options.length === 0 && (
          <TextBlock className="text-xs text-mist">
            Tidak ada karyawan divisi ini yang belum masuk tim. Atur divisi karyawan di menu Direktori.
          </TextBlock>
        )}
      </div>
    </VmsDialog>
  );
}
