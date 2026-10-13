import { useState } from "react";
import { toast } from "sonner";
import { ActionButton } from "@/components/molecules/ActionButton";
import { CheckControl } from "@/components/molecules/CheckControl";
import { DialogActions } from "@/components/molecules/DialogActions";
import { SelectField, TextAreaField, TextField } from "@/components/molecules/Field";
import { ControlLabel, ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { FormErrorText } from "@/components/molecules/FormErrorText";
import { ExternalLink } from "@/components/molecules/Links";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { Pill } from "@/components/molecules/Pill";
import {
  TableBlock,
  TableBlockBody,
  TableBlockCell,
  TableBlockHead,
  TableBlockHeaderCell,
  TableBlockRow,
} from "@/components/molecules/TableBlock";
import { TextBlock } from "@/components/molecules/TextBlock";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { Edit2, Plus, Trash2 } from "@/components/molecules/Glyphs";
import { errorMessage } from "@/lib/errors";
import {
  useCreateEmergencyContact,
  useDeleteEmergencyContact,
  useEmergencyContacts,
  useUpdateEmergencyContact,
  type EmergencyContact,
} from "@/services/employeeService";

const RELATIONSHIP_OPTIONS = [
  "Istri",
  "Suami",
  "Orang Tua",
  "Anak",
  "Saudara",
  "Kerabat",
  "Teman",
  "Lainnya",
] as const;

interface EmergencyContactFormDialogProps {
  initial?: EmergencyContact | null;
  onClose: () => void;
  onSubmit: (values: {
    name: string;
    relationship: string;
    phone: string;
    address: string | null;
    is_primary: boolean;
  }) => Promise<void>;
  busy: boolean;
}

function EmergencyContactFormDialog({
  initial,
  onClose,
  onSubmit,
  busy,
}: EmergencyContactFormDialogProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [relationship, setRelationship] = useState(initial?.relationship ?? "Keluarga");
  const [phone, setPhone] = useState(initial?.phone ?? "");
  const [address, setAddress] = useState(initial?.address ?? "");
  const [isPrimary, setIsPrimary] = useState(initial?.is_primary ?? true);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return setError("Nama kontak darurat wajib diisi.");
    if (!phone.trim()) return setError("No. telepon darurat wajib diisi.");

    setError(null);
    try {
      await onSubmit({
        name: name.trim(),
        relationship: relationship.trim(),
        phone: phone.trim(),
        address: address.trim() || null,
        is_primary: isPrimary,
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <VmsDialog
      open
      title={initial ? "Ubah kontak darurat" : "Tambah kontak darurat"}
      onClose={onClose}
      footer={
        <DialogActions onCancel={onClose} busy={busy} formId="emergency-contact-form" />
      }
    >
      <FormBlock id="emergency-contact-form" onSubmit={handleSubmit} noValidate>
        <FormErrorText message={error} />
        <TextField
          label="Nama lengkap"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nama keluarga atau kerabat"
        />
        <SelectField
          label="Hubungan"
          value={relationship}
          onChange={(e) => setRelationship(e.target.value)}
        >
          {RELATIONSHIP_OPTIONS.map((rel) => (
            <ControlOption key={rel} value={rel}>
              {rel}
            </ControlOption>
          ))}
        </SelectField>
        <TextField
          label="No. telepon"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="081234567890"
        />
        <TextAreaField
          label="Alamat (opsional)"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Alamat tempat tinggal kontak darurat"
        />
        <div className="flex items-center gap-2 pt-1">
          <CheckControl
            id="is-primary-checkbox"
            checked={isPrimary}
            onCheckedChange={(c) => setIsPrimary(!!c)}
          />
          <ControlLabel htmlFor="is-primary-checkbox" className="text-sm font-medium cursor-pointer">
            Jadikan sebagai kontak darurat utama
          </ControlLabel>
        </div>
      </FormBlock>
    </VmsDialog>
  );
}

export function EmergencyContactsPanel({
  employeeId,
  canEdit,
}: {
  employeeId: string;
  canEdit: boolean;
}) {
  const { data: contacts, isLoading, isError } = useEmergencyContacts(employeeId);
  const createMutation = useCreateEmergencyContact(employeeId);
  const updateMutation = useUpdateEmergencyContact(employeeId);
  const deleteMutation = useDeleteEmergencyContact(employeeId);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingContact, setEditingContact] = useState<EmergencyContact | null>(null);
  const [deletingContact, setDeletingContact] = useState<EmergencyContact | null>(null);

  const handleOpenAdd = () => {
    setEditingContact(null);
    setDialogOpen(true);
  };

  const handleOpenEdit = (contact: EmergencyContact) => {
    setEditingContact(contact);
    setDialogOpen(true);
  };

  const handleSave = async (values: {
    name: string;
    relationship: string;
    phone: string;
    address: string | null;
    is_primary: boolean;
  }) => {
    if (editingContact) {
      await updateMutation.mutateAsync({
        contactId: editingContact.id,
        ...values,
      });
      toast.success("Kontak darurat berhasil diperbarui.");
    } else {
      await createMutation.mutateAsync(values);
      toast.success("Kontak darurat berhasil ditambahkan.");
    }
  };

  const handleDelete = async (contact: EmergencyContact) => {
    try {
      await deleteMutation.mutateAsync(contact.id);
      toast.success("Kontak darurat berhasil dihapus.");
      setDeletingContact(null);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <section aria-label="Kontak darurat" className="mb-8">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <TextBlock as="h3" className="font-semibold text-foreground">
            Kontak Darurat
          </TextBlock>
          <TextBlock className="text-xs text-mist">
            Data kontak darurat untuk keperluan situasi darurat atau keselamatan kerja.
          </TextBlock>
        </div>
        {canEdit && (
          <ActionButton size="sm" onClick={handleOpenAdd}>
            <Plus className="mr-1.5 h-4 w-4" />
            Tambah kontak
          </ActionButton>
        )}
      </div>

      <div className="overflow-hidden rounded-panel border border-line bg-surface shadow-card">
        {isLoading ? (
          <div className="p-6">
            <LoadingBar />
          </div>
        ) : isError ? (
          <TextBlock className="p-6 text-center text-sm text-destructive">
            Gagal memuat kontak darurat.
          </TextBlock>
        ) : !contacts || contacts.length === 0 ? (
          <TextBlock className="p-6 text-center text-sm text-mist">
            Belum ada kontak darurat terdaftar.
          </TextBlock>
        ) : (
          <TableBlock>
            <TableBlockHead>
              <TableBlockRow>
                <TableBlockHeaderCell>Nama</TableBlockHeaderCell>
                <TableBlockHeaderCell>Hubungan</TableBlockHeaderCell>
                <TableBlockHeaderCell>No. Telepon</TableBlockHeaderCell>
                <TableBlockHeaderCell>Alamat</TableBlockHeaderCell>
                {canEdit && <TableBlockHeaderCell className="text-right">Aksi</TableBlockHeaderCell>}
              </TableBlockRow>
            </TableBlockHead>
            <TableBlockBody>
              {contacts.map((c) => (
                <TableBlockRow key={c.id}>
                  <TableBlockCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <TextBlock as="span">{c.name}</TextBlock>
                      {c.is_primary && <Pill tone="success">Utama</Pill>}
                    </div>
                  </TableBlockCell>
                  <TableBlockCell>
                    <Pill tone="neutral">{c.relationship}</Pill>
                  </TableBlockCell>
                  <TableBlockCell>
                    <ExternalLink
                      href={`tel:${c.phone}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {c.phone}
                    </ExternalLink>
                  </TableBlockCell>
                  <TableBlockCell className="text-mist">{c.address || "-"}</TableBlockCell>
                  {canEdit && (
                    <TableBlockCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <ActionButton
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenEdit(c)}
                          title="Ubah kontak"
                        >
                          <Edit2 className="h-4 w-4" />
                        </ActionButton>
                        <ActionButton
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeletingContact(c)}
                          title="Hapus kontak"
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </ActionButton>
                      </div>
                    </TableBlockCell>
                  )}
                </TableBlockRow>
              ))}
            </TableBlockBody>
          </TableBlock>
        )}
      </div>

      {/* Dialog Form Tambah/Ubah */}
      {dialogOpen && (
        <EmergencyContactFormDialog
          initial={editingContact}
          onClose={() => setDialogOpen(false)}
          onSubmit={handleSave}
          busy={createMutation.isPending || updateMutation.isPending}
        />
      )}

      {/* Dialog Konfirmasi Hapus */}
      {deletingContact && (
        <VmsDialog
          open
          title="Hapus kontak darurat"
          onClose={() => setDeletingContact(null)}
          footer={
            <div className="flex justify-end gap-2">
              <ActionButton
                variant="outline"
                onClick={() => setDeletingContact(null)}
                disabled={deleteMutation.isPending}
              >
                Batal
              </ActionButton>
              <ActionButton
                variant="destructive"
                onClick={() => handleDelete(deletingContact)}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? "Menghapus..." : "Hapus"}
              </ActionButton>
            </div>
          }
        >
          <TextBlock className="text-sm">
            Apakah Anda yakin ingin menghapus kontak darurat{" "}
            <TextBlock as="strong" className="font-semibold">{deletingContact.name}</TextBlock>? Tindakan ini tidak dapat
            dibatalkan.
          </TextBlock>
        </VmsDialog>
      )}
    </section>
  );
}
