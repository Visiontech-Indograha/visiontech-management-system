import { useState } from "react";
import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { ActionButton } from "@/components/molecules/ActionButton";
import { TextBlock } from "@/components/molecules/TextBlock";
import { TextField, TextAreaField, SelectField } from "@/components/molecules/Field";
import { FormBlock, ControlOption } from "@/components/molecules/FormBlock";
import { Plus } from "@/components/molecules/Glyphs";
import { useClients, useClientSites } from "@/services/clientService";
import { useDivisions } from "@/services/employeeService";
import { useTeams } from "@/services/teamService";
import { useCreateWorkOrder, usePmCandidates } from "@/services/workOrderService";
import { useSession } from "@/stores/sessionStore";
import { divisionScopeIds } from "@/lib/divisionScope";
import { applyFieldErrors, errorMessage } from "@/lib/errors";

/** Batas judul sama dengan API (WorkOrderCreate.title: 3 sampai 200 karakter). */
export const WO_TITLE_MIN = 3;
export const WO_TITLE_MAX = 200;

interface WorkOrderCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultDivisionId?: string;
}

export function WorkOrderCreateModal({
  isOpen,
  onClose,
  defaultDivisionId,
}: WorkOrderCreateModalProps) {
  const [clientId, setClientId] = useState("");
  const [clientSiteId, setClientSiteId] = useState("");
  const [divisionId, setDivisionId] = useState(defaultDivisionId || "");
  const [pmId, setPmId] = useState("");
  const [title, setTitle] = useState("");
  const [initialComplaint, setInitialComplaint] = useState("");
  const [leadTeamId, setLeadTeamId] = useState("");
  const [titleError, setTitleError] = useState("");

  const { me } = useSession();
  // PM hanya boleh memilih divisinya sendiri; OM/SA tetap bebas memilih.
  const scopeIds = divisionScopeIds(me);
  const scopedDivisionId = scopeIds
    ? (scopeIds.includes(divisionId) ? divisionId : (scopeIds[0] ?? ""))
    : divisionId;

  const { data: clients = [] } = useClients();
  const { data: sites = [] } = useClientSites(clientId);
  const { data: allDivisions = [] } = useDivisions();
  const divisions = scopeIds ? allDivisions.filter((d) => scopeIds.includes(d.id)) : allDivisions;
  const { data: teams = [] } = useTeams();

  const pmQuery = usePmCandidates(scopedDivisionId || undefined);
  const pmOptions = pmQuery.data ?? [];
  const pmHint = pmQuery.isPending
    ? "Memuat daftar PM..."
    : pmQuery.isError
      ? undefined
      : pmOptions.length === 0
        ? "Belum ada PM di divisi ini"
        : undefined;
  const pmError = pmQuery.isError ? "Daftar PM belum bisa dimuat. Tutup lalu buka lagi, atau coba beberapa saat lagi." : undefined;

  const createMutation = useCreateWorkOrder();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientId) {
      toast.error("Pilih klien terlebih dahulu");
      return;
    }
    const finalDivisionId = scopedDivisionId || (divisions.length > 0 ? divisions[0].id : "");
    if (!finalDivisionId) {
      toast.error("Pilih divisi terlebih dahulu");
      return;
    }
    const finalPmId = pmId || (pmOptions.length === 1 ? pmOptions[0].employee_id : "");
    if (!finalPmId) {
      toast.error("Pilih Project Manager (PM) penanggung jawab");
      return;
    }
    setTitleError("");
    if (!title.trim()) {
      setTitleError("Judul tugas atau pekerjaan wajib diisi.");
      return;
    }
    if (title.trim().length < WO_TITLE_MIN) {
      setTitleError(`Judul minimal ${WO_TITLE_MIN} karakter.`);
      return;
    }
    if (title.trim().length > WO_TITLE_MAX) {
      setTitleError(`Judul maksimal ${WO_TITLE_MAX} karakter.`);
      return;
    }

    try {
      const created = await createMutation.mutateAsync({
        client_id: clientId,
        client_site_id: clientSiteId || undefined,
        division_id: finalDivisionId,
        pm_id: finalPmId,
        title: title.trim(),
        initial_complaint: initialComplaint.trim() || undefined,
        lead_team_id: leadTeamId || undefined,
      });
      toast.success("Tugas klien baru berhasil dibuat");
      if (created.duplicate_title_warning) toast.warning(created.duplicate_title_warning);
      onClose();
    } catch (err) {
      const setField = (name: string, e: { message: string }) => {
        if (name === "title") setTitleError(e.message);
      };
      if (applyFieldErrors(err, setField as never, ["title"])) return;
      toast.error(errorMessage(err, "Gagal membuat tugas klien"));
    }
  };

  if (!isOpen) return null;

  return (
    <VmsDialog
      open={isOpen}
      onClose={onClose}
      title="Buat Tugas Klien Baru"
      size="xl"
      footer={
        <div className="flex justify-end gap-2 w-full">
          <ActionButton
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={createMutation.isPending}
          >
            <TextBlock as="span">Batal</TextBlock>
          </ActionButton>
          <ActionButton
            type="submit"
            form="create-wo-form"
            variant="default"
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? (
              <TextBlock as="span">Menyimpan...</TextBlock>
            ) : (
              <div className="flex items-center gap-1.5">
                <Plus className="h-4 w-4" />
                <TextBlock as="span">Simpan tugas klien</TextBlock>
              </div>
            )}
          </ActionButton>
        </div>
      }
    >
      <FormBlock id="create-wo-form" noValidate onSubmit={handleSubmit} className="space-y-4 pt-2">
        <div className="space-y-3">
          <TextField
            label="Judul Tugas / Pekerjaan *"
            placeholder="Contoh: Perbaikan Kabel Fiber Optic Cut Ruas Fatmawati"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={WO_TITLE_MAX}
            error={titleError || undefined}
            required
          />

          <SelectField
            label="Klien Pemilik Tugas *"
            value={clientId}
            onChange={(e) => {
              setClientId(e.target.value);
              setClientSiteId("");
            }}
            required
          >
            <ControlOption value="">Pilih klien</ControlOption>
            {clients.map((c) => (
              <ControlOption key={c.client_id} value={c.client_id}>
                {c.name}
              </ControlOption>
            ))}
          </SelectField>

          {clientId && (
            <SelectField
              label="Cabang / Lokasi Site Klien"
              value={clientSiteId}
              onChange={(e) => setClientSiteId(e.target.value)}
              hint={sites.length === 0 ? "Klien belum memiliki daftar lokasi cabang/site." : undefined}
            >
              <ControlOption value="">Pilih lokasi cabang (opsional)</ControlOption>
              {sites.map((s) => (
                <ControlOption key={s.site_id} value={s.site_id}>
                  {s.site_name} - {s.address}
                </ControlOption>
              ))}
            </SelectField>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <SelectField
              label="Divisi kerja *"
              value={scopedDivisionId}
              onChange={(e) => setDivisionId(e.target.value)}
              required
            >
              <ControlOption value="">Pilih divisi</ControlOption>
              {divisions.map((d) => (
                <ControlOption key={d.id} value={d.id}>
                  {d.name}
                </ControlOption>
              ))}
            </SelectField>

            <SelectField
              label="Project Manager (PM) *"
              value={pmId}
              onChange={(e) => setPmId(e.target.value)}
              required
              hint={pmHint}
              error={pmError}
              aria-busy={pmQuery.isPending}
            >
              <ControlOption value="">Pilih PM</ControlOption>
              {pmOptions.map((emp) => (
                <ControlOption key={emp.employee_id} value={emp.employee_id}>
                  {emp.full_name}
                </ControlOption>
              ))}
            </SelectField>
          </div>

          <SelectField
            label="Tim survei (opsional)"
            value={leadTeamId}
            onChange={(e) => setLeadTeamId(e.target.value)}
            hint="Bisa ditentukan sekarang atau saat statusnya menunggu survei"
          >
            <ControlOption value="">Belum ditugaskan</ControlOption>
            {teams.map((t) => (
              <ControlOption key={t.team_id} value={t.team_id}>
                {t.name} (Ketua: {t.leader_name || "-"})
              </ControlOption>
            ))}
          </SelectField>

          <TextAreaField
            label="Keluhan Klien / Catatan Awal"
            placeholder="Jelaskan kebutuhan, masalah awal, atau ekspektasi yang dilaporkan klien..."
            value={initialComplaint}
            onChange={(e) => setInitialComplaint(e.target.value)}
            rows={3}
          />
        </div>
      </FormBlock>
    </VmsDialog>
  );
}
