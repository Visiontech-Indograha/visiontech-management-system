import { useState } from "react";
import { toast } from "sonner";
import { VmsDialog } from "@/components/molecules/VmsDialog";
import { SelectField, TextField } from "@/components/molecules/Field";
import { ApiError } from "@/lib/apiClient";
import { formatDate } from "@/lib/format";
import {
  useCreateDocument,
  useDeactivateDocument,
  useDeleteDocument,
  useEmployeeDocuments,
  useUploadFile,
  type EmployeeDocument,
} from "@/services/employeeService";
import { FilePreview } from "@/components/molecules/FilePreview";
import { Pill } from "@/components/molecules/Pill";
import { ActionButton } from "@/components/molecules/ActionButton";
import { LoadingBar } from "@/components/molecules/LoadingBar";
import { TextBlock } from "@/components/molecules/TextBlock";
import { TableBlock, TableBlockBody, TableBlockCell, TableBlockHead, TableBlockHeaderCell, TableBlockRow } from "@/components/molecules/TableBlock";
import { ControlInput, ControlOption, FormBlock } from "@/components/molecules/FormBlock";
import { DialogActions } from "@/components/molecules/DialogActions";
import { FormErrorText } from "@/components/molecules/FormErrorText";

type Errors = Record<string, string>;

/** Kode baku employee_file.type (sama dengan seed V2); API juga merapikan ketikan bebas ke bentuk ini. */
const DOC_TYPES: Record<string, string> = {
  KTP: "KTP",
  SIM_A: "SIM A",
  SIM_B1: "SIM B I",
  SIM_B2: "SIM B II",
  SIM_C: "SIM C",
  MCU: "Medical check-up",
  SERTIFIKAT_K3: "Sertifikat K3",
  SERTIFIKAT_TEKNIS: "Sertifikat teknis",
  KONTRAK_PKWT: "Kontrak PKWT",
};
const OTHER = "__other__";
const docLabel = (code: string) => DOC_TYPES[code] ?? code.split("_").join(" ");

const STATUS: Record<EmployeeDocument["status"], { label: string; tone: "success" | "warning" | "danger" }> = {
  active: { label: "Berlaku", tone: "success" },
  extended: { label: "Diganti", tone: "warning" },
  not_active: { label: "Tidak berlaku", tone: "danger" },
};

/** Sisa hari sampai kedaluwarsa menurut tanggal WIB (peringatan ≤ 30 hari). */
function daysUntil(isoDate: string): number {
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
  return Math.round((Date.parse(isoDate) - Date.parse(today)) / 86_400_000);
}

function ExpiryWarning({ doc }: { doc: EmployeeDocument }) {
  if (!doc.expired_at || doc.status !== "active") return null;
  const days = daysUntil(doc.expired_at);
  if (days < 0) return <Pill tone="danger">Kedaluwarsa</Pill>;
  if (days <= 30) return <Pill tone="warning">{days === 0 ? "Berakhir hari ini" : `${days} hari lagi`}</Pill>;
  return null;
}

/**
 * Dokumen & sertifikat karyawan (employee_file). Karyawan melihat miliknya; HR/GA (`canManage`) menambah,
 * memperbarui (dokumen sejenis yang baru menggantikan yang lama), menonaktifkan, dan menghapus salah unggah.
 */
export function DocumentsPanel({ employeeId, canManage }: { employeeId: string; canManage: boolean }) {
  const docs = useEmployeeDocuments(employeeId);
  const deactivate = useDeactivateDocument(employeeId);
  const remove = useDeleteDocument(employeeId);
  const [editing, setEditing] = useState(false);
  const [renewing, setRenewing] = useState<EmployeeDocument | null>(null);
  const columns = canManage ? 6 : 5;

  const act = (run: Promise<unknown>, done: string) =>
    run.then(
      () => toast.success(done),
      (err) => toast.error(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi."),
    );

  return (
    <section aria-label="Berkas">
      <div className="mb-3 flex items-center justify-between">
        <TextBlock as="h2" className="text-base font-semibold">Berkas</TextBlock>
        {canManage && <ActionButton onClick={() => setEditing(true)}>Tambah berkas</ActionButton>}
      </div>

      <div className="overflow-x-auto rounded-panel border border-line bg-surface shadow-card">
        <TableBlock className="w-full text-left text-sm">
          <TableBlockHead className="border-b border-line text-mist">
            <TableBlockRow>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Berkas</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Berlaku sejak</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Kedaluwarsa</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">Status</TableBlockHeaderCell>
              <TableBlockHeaderCell className="px-4 py-3 font-medium">File</TableBlockHeaderCell>
              {canManage && <TableBlockHeaderCell className="px-4 py-3 text-right font-medium">Aksi</TableBlockHeaderCell>}
            </TableBlockRow>
          </TableBlockHead>
          <TableBlockBody>
            {docs.isPending && (
              <TableBlockRow aria-hidden>
                <TableBlockCell colSpan={columns} className="px-4 py-3">
                  <LoadingBar className="h-4 w-1/2" />
                </TableBlockCell>
              </TableBlockRow>
            )}
            {docs.isError && (
              <TableBlockRow>
                <TableBlockCell colSpan={columns} className="px-4 py-6 text-center text-danger">
                  Berkas tidak dapat dimuat.{" "}
                  <ActionButton variant="outline" size="sm" onClick={() => docs.refetch()}>
                    Coba lagi
                  </ActionButton>
                </TableBlockCell>
              </TableBlockRow>
            )}
            {docs.data?.items.length === 0 && (
              <TableBlockRow>
                <TableBlockCell colSpan={columns} className="px-4 py-6 text-center text-mist">
                  Belum ada berkas.
                </TableBlockCell>
              </TableBlockRow>
            )}
            {docs.data?.items.map((d) => (
              <TableBlockRow key={d.id} className="h-11 border-b border-line last:border-0">
                <TableBlockCell className="px-4 py-2 font-medium">{docLabel(d.doc_type)}</TableBlockCell>
                <TableBlockCell className="px-4 py-2">{formatDate(d.active_at)}</TableBlockCell>
                <TableBlockCell className="px-4 py-2">
                  {d.expired_at ? (
                    <TextBlock as="span" className="flex flex-wrap items-center gap-2">
                      {formatDate(d.expired_at)}
                      <ExpiryWarning doc={d} />
                    </TextBlock>
                  ) : (
                    "-"
                  )}
                </TableBlockCell>
                <TableBlockCell className="px-4 py-2">
                  <Pill tone={STATUS[d.status].tone}>{STATUS[d.status].label}</Pill>
                </TableBlockCell>
                <TableBlockCell className="px-4 py-2">
                  {d.file_id ? <FilePreview fileId={d.file_id} fileName={docLabel(d.doc_type)} /> : "-"}
                </TableBlockCell>
                {canManage && (
                  <TableBlockCell className="px-4 py-2 text-right">
                    <TextBlock as="span" className="inline-flex gap-2">
                      {d.status === "active" && (
                        <>
                          <ActionButton size="sm" variant="outline" aria-label={`Perbarui ${docLabel(d.doc_type)}`} onClick={() => setRenewing(d)}>
                            Perbarui
                          </ActionButton>
                          <ActionButton
                            size="sm"
                            variant="outline"
                            disabled={deactivate.isPending}
                            onClick={() => act(deactivate.mutateAsync(d.id), `${docLabel(d.doc_type)} dinonaktifkan.`)}
                          >
                            Nonaktifkan
                          </ActionButton>
                        </>
                      )}
                      <ActionButton
                        size="sm"
                        variant="outline"
                        disabled={remove.isPending}
                        onClick={() => {
                          if (window.confirm(`Hapus ${docLabel(d.doc_type)}? Pakai ini hanya untuk berkas yang salah unggah.`)) {
                            void act(remove.mutateAsync(d.id), `${docLabel(d.doc_type)} dihapus.`);
                          }
                        }}
                      >
                        Hapus
                      </ActionButton>
                    </TextBlock>
                  </TableBlockCell>
                )}
              </TableBlockRow>
            ))}
          </TableBlockBody>
        </TableBlock>
      </div>

      {editing && <DocumentDialog employeeId={employeeId} onClose={() => setEditing(false)} />}
      {renewing && <DocumentDialog employeeId={employeeId} renew={renewing} onClose={() => setRenewing(null)} />}
    </section>
  );
}

function DocumentDialog({
  employeeId,
  renew,
  onClose,
}: {
  employeeId: string;
  /** Dokumen yang diperbarui: jenisnya tetap; yang baru menggantikannya (lama → "Diganti"). */
  renew?: EmployeeDocument;
  onClose: () => void;
}) {
  const upload = useUploadFile();
  const create = useCreateDocument(employeeId);
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [other, setOther] = useState(false);
  const pending = upload.isPending || create.isPending;

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const picked = String(f.get("doc_type") ?? "");
    const doc_type = (picked === OTHER ? String(f.get("doc_type_other") ?? "") : picked).trim();
    const active_at = String(f.get("active_at") ?? "").trim() || null;
    const expired_at = String(f.get("expired_at") ?? "").trim() || null;
    const fileInput = e.currentTarget.elements.namedItem("file") as HTMLInputElement;
    const file = fileInput.files?.[0];

    setErrors({});
    setFormError(null);

    if (!doc_type) return setErrors({ doc_type: "Wajib diisi." });
    if (active_at && expired_at && expired_at < active_at) return setErrors({ expired_at: "Tidak boleh sebelum tanggal berlaku." });
    if (!file || file.size === 0) return setErrors({ file: "File wajib dilampirkan." });

    try {
      const fileForm = new FormData();
      fileForm.set("file", file);
      const { file_id } = await upload.mutateAsync(fileForm);
      await create.mutateAsync({ doc_type, file_id, active_at, expired_at });
      toast.success(renew ? "Berkas diperbarui." : "Berkas ditambahkan.");
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details.fields) setErrors(err.details.fields as Errors);
      else setFormError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    }
  };

  return (
    <VmsDialog
      open
      title={renew ? "Perbarui berkas" : "Tambah berkas"}
      onClose={onClose}
      footer={<DialogActions onCancel={onClose} busy={pending} formId="document-form" />}
    >
      <FormBlock id="document-form" onSubmit={submit} noValidate>
        <FormErrorText message={formError} />
        {renew ? (
          <TextBlock className="mb-4 text-sm">
            <ControlInput type="hidden" name="doc_type" value={renew.doc_type} />
            <TextBlock as="span" className="text-mist">Jenis dokumen: </TextBlock>
            <TextBlock as="span" className="font-medium">{docLabel(renew.doc_type)}</TextBlock>
            {renew.expired_at && <TextBlock as="span" className="text-mist"> · berlaku sampai {formatDate(renew.expired_at)}</TextBlock>}
          </TextBlock>
        ) : (
          <>
            <SelectField
              name="doc_type"
              label="Jenis dokumen"
              error={errors.doc_type}
              defaultValue=""
              onChange={(e) => setOther(e.target.value === OTHER)}
            >
              <ControlOption value="" disabled>
                Pilih jenis dokumen
              </ControlOption>
              {Object.entries(DOC_TYPES).map(([code, label]) => (
                <ControlOption key={code} value={code}>
                  {label}
                </ControlOption>
              ))}
              <ControlOption value={OTHER}>Lainnya…</ControlOption>
            </SelectField>
            {other && <TextField name="doc_type_other" label="Jenis dokumen lainnya" hint="Contoh: SIO Excavator, Drone Pilot" />}
          </>
        )}
        <TextField name="active_at" label="Berlaku sejak" type="date" error={errors.active_at} hint="Kosongkan bila berlaku hari ini." />
        <TextField name="expired_at" label="Tanggal kedaluwarsa" type="date" error={errors.expired_at} hint="Bila ada." />
        <TextField name="file" label="File (jpg, png, pdf; maks. 10 MB)" type="file" accept=".jpg,.jpeg,.png,.pdf" error={errors.file} />
      </FormBlock>
    </VmsDialog>
  );
}
