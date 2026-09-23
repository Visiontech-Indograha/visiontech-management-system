import { useState } from "react";
import {
  useInternalDocuments,
  useCreateInternalDocument,
  useUpdateInternalDocument,
  useDeleteInternalDocument,
  useOutpostLetters,
  useCreateOutpostLetter,
  useUpdateOutpostLetter,
  useDeleteOutpostLetter,
} from "../../hooks/api/useDocument";
import { useEmployees } from "../../hooks/api/useLookups";
import { DocumentType, InternalDocument, OutpostLetter } from "../../types/document";
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from "../../components/ui/Table";
import { Button } from "../../components/ui/Button";
import { Input, Select, TextArea } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { DetailDrawer, DetailField } from "../../components/ui/DetailDrawer";
import { LoadingState, ErrorState, EmptyTableRow } from "../../components/ui/QueryState";
import toast from "react-hot-toast";

const EMPTY_INTERNAL_FORM = {
  document_type: DocumentType.HES_PLAN,
  title: "",
  description: "",
  upload_date: new Date().toISOString().split("T")[0],
  file_url: "",
};

const EMPTY_OUTPOST_FORM = {
  letter_number: "",
  subject: "",
  issue_date: new Date().toISOString().split("T")[0],
  employee_id: "",
  file_url: "",
};

const InternalDocumentPage = () => {
  const [tab, setTab] = useState<"internal" | "outpost">("internal");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dokumen</h1>
        <p className="mt-1 text-sm text-gray-500">Kelola dokumen internal (HES Plan, SOP, Kebijakan) dan surat keluar/tugas.</p>
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {(["internal", "outpost"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`${tab === t ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"} whitespace-nowrap border-b-2 px-1 pb-4 text-sm font-medium`}
            >
              {t === "internal" ? "Dokumen Internal" : "Surat Keluar"}
            </button>
          ))}
        </nav>
      </div>

      {tab === "internal" ? <InternalDocumentTab /> : <OutpostLetterTab />}
    </div>
  );
};

const InternalDocumentTab = () => {
  const { data: documents, isLoading, error } = useInternalDocuments();
  const createMutation = useCreateInternalDocument();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<InternalDocument | null>(null);
  const [detailTarget, setDetailTarget] = useState<InternalDocument | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<InternalDocument | null>(null);
  const [form, setForm] = useState(EMPTY_INTERNAL_FORM);

  const updateMutation = useUpdateInternalDocument(editing?.id || "");
  const deleteMutation = useDeleteInternalDocument();

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_INTERNAL_FORM);
    setIsModalOpen(true);
  };

  const openEdit = (doc: InternalDocument) => {
    setEditing(doc);
    setForm({
      document_type: doc.document_type,
      title: doc.title,
      description: doc.description || "",
      upload_date: doc.upload_date.split("T")[0],
      file_url: doc.file_url || "",
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = { ...form, file_url: form.file_url || undefined };
      if (editing) {
        await updateMutation.mutateAsync(payload);
        toast.success("Dokumen berhasil diperbarui");
      } else {
        await createMutation.mutateAsync(payload);
        toast.success("Dokumen berhasil ditambahkan");
      }
      setIsModalOpen(false);
      setEditing(null);
      setForm(EMPTY_INTERNAL_FORM);
    } catch {
      // Error sudah ditampilkan oleh interceptor global di lib/api.ts
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteMutation.mutateAsync(deleteTarget.id);
    toast.success("Dokumen berhasil dihapus");
    setDeleteTarget(null);
  };

  if (isLoading) return <LoadingState label="Loading dokumen internal..." />;
  if (error) return <ErrorState label="Gagal memuat dokumen internal." />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={openCreate}>+ Upload Dokumen</Button>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Tipe</TableHeader>
              <TableHeader>Judul</TableHeader>
              <TableHeader>Tanggal</TableHeader>
              <TableHeader>Deskripsi</TableHeader>
              <TableHeader>Aksi</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {!documents || documents.length === 0 ? (
              <EmptyTableRow colSpan={5} label="Belum ada dokumen." />
            ) : (
              documents.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell>{doc.document_type}</TableCell>
                  <TableCell>{doc.title}</TableCell>
                  <TableCell>{new Date(doc.upload_date).toLocaleDateString()}</TableCell>
                  <TableCell>{doc.description || "-"}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-3">
                      <button onClick={() => setDetailTarget(doc)} className="text-gray-600 hover:underline text-sm">Detail</button>
                      <button onClick={() => openEdit(doc)} className="text-indigo-600 hover:underline text-sm">Edit</button>
                      <button onClick={() => setDeleteTarget(doc)} className="text-red-600 hover:underline text-sm">Hapus</button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editing ? "Edit Dokumen" : "Upload Dokumen"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Select
            label="Tipe Dokumen"
            value={form.document_type}
            onChange={(e) => setForm({ ...form, document_type: e.target.value as DocumentType })}
          >
            <option value={DocumentType.HES_PLAN}>HES Plan</option>
            <option value={DocumentType.SOP}>SOP</option>
            <option value={DocumentType.POLICY}>Policy</option>
            <option value={DocumentType.OTHER}>Other</option>
          </Select>
          <Input
            label="Judul"
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <TextArea
            label="Deskripsi"
            rows={3}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <Input
            label="Tanggal"
            required
            type="date"
            value={form.upload_date}
            onChange={(e) => setForm({ ...form, upload_date: e.target.value })}
          />
          <Input
            label="URL File (Opsional)"
            value={form.file_url}
            onChange={(e) => setForm({ ...form, file_url: e.target.value })}
          />
          <ModalFooter onCancel={() => setIsModalOpen(false)} isSubmitting={createMutation.isPending || updateMutation.isPending} />
        </form>
      </Modal>

      <DetailDrawer isOpen={!!detailTarget} onClose={() => setDetailTarget(null)} title={detailTarget?.title || "Detail Dokumen"}>
        {detailTarget && (
          <dl>
            <DetailField label="Tipe" value={detailTarget.document_type} />
            <DetailField label="Judul" value={detailTarget.title} />
            <DetailField label="Deskripsi" value={detailTarget.description} />
            <DetailField label="Tanggal Upload" value={new Date(detailTarget.upload_date).toLocaleDateString()} />
            <DetailField
              label="File"
              value={detailTarget.file_url ? <a href={detailTarget.file_url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline">Buka File</a> : null}
            />
          </dl>
        )}
      </DetailDrawer>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        message={`Hapus dokumen "${deleteTarget?.title}"?`}
        isConfirming={deleteMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};

const OutpostLetterTab = () => {
  const { data: letters, isLoading, error } = useOutpostLetters();
  const { data: employees } = useEmployees();
  const createMutation = useCreateOutpostLetter();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<OutpostLetter | null>(null);
  const [detailTarget, setDetailTarget] = useState<OutpostLetter | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<OutpostLetter | null>(null);
  const [form, setForm] = useState(EMPTY_OUTPOST_FORM);

  const updateMutation = useUpdateOutpostLetter(editing?.id || "");
  const deleteMutation = useDeleteOutpostLetter();

  const employeeName = (id: string) => employees?.find((e) => e.id === id)?.full_name || id;

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_OUTPOST_FORM);
    setIsModalOpen(true);
  };

  const openEdit = (letter: OutpostLetter) => {
    setEditing(letter);
    setForm({
      letter_number: letter.letter_number,
      subject: letter.subject,
      issue_date: letter.issue_date.split("T")[0],
      employee_id: letter.employee_id,
      file_url: letter.file_url || "",
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.employee_id) {
      toast.error("Silakan pilih karyawan");
      return;
    }
    try {
      const payload = { ...form, file_url: form.file_url || undefined };
      if (editing) {
        await updateMutation.mutateAsync(payload);
        toast.success("Surat berhasil diperbarui");
      } else {
        await createMutation.mutateAsync(payload);
        toast.success("Surat berhasil ditambahkan");
      }
      setIsModalOpen(false);
      setEditing(null);
      setForm(EMPTY_OUTPOST_FORM);
    } catch {
      // Error sudah ditampilkan oleh interceptor global di lib/api.ts
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteMutation.mutateAsync(deleteTarget.id);
    toast.success("Surat berhasil dihapus");
    setDeleteTarget(null);
  };

  if (isLoading) return <LoadingState label="Loading surat keluar..." />;
  if (error) return <ErrorState label="Gagal memuat surat keluar." />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={openCreate}>+ Buat Surat</Button>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>No. Surat</TableHeader>
              <TableHeader>Perihal</TableHeader>
              <TableHeader>Karyawan</TableHeader>
              <TableHeader>Tanggal</TableHeader>
              <TableHeader>Aksi</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {!letters || letters.length === 0 ? (
              <EmptyTableRow colSpan={5} label="Belum ada surat keluar." />
            ) : (
              letters.map((letter) => (
                <TableRow key={letter.id}>
                  <TableCell>{letter.letter_number}</TableCell>
                  <TableCell>{letter.subject}</TableCell>
                  <TableCell>{employeeName(letter.employee_id)}</TableCell>
                  <TableCell>{new Date(letter.issue_date).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-3">
                      <button onClick={() => setDetailTarget(letter)} className="text-gray-600 hover:underline text-sm">Detail</button>
                      <button onClick={() => openEdit(letter)} className="text-indigo-600 hover:underline text-sm">Edit</button>
                      <button onClick={() => setDeleteTarget(letter)} className="text-red-600 hover:underline text-sm">Hapus</button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editing ? "Edit Surat Keluar" : "Buat Surat Keluar"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Nomor Surat"
            required
            value={form.letter_number}
            onChange={(e) => setForm({ ...form, letter_number: e.target.value })}
          />
          <Input
            label="Perihal"
            required
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
          />
          <Select
            label="Karyawan"
            required
            value={form.employee_id}
            onChange={(e) => setForm({ ...form, employee_id: e.target.value })}
          >
            <option value="" disabled>Pilih Karyawan</option>
            {employees?.map((emp) => (
              <option key={emp.id} value={emp.id}>{emp.full_name}</option>
            ))}
          </Select>
          <Input
            label="Tanggal Terbit"
            required
            type="date"
            value={form.issue_date}
            onChange={(e) => setForm({ ...form, issue_date: e.target.value })}
          />
          <Input
            label="URL File (Opsional)"
            value={form.file_url}
            onChange={(e) => setForm({ ...form, file_url: e.target.value })}
          />
          <ModalFooter onCancel={() => setIsModalOpen(false)} isSubmitting={createMutation.isPending || updateMutation.isPending} />
        </form>
      </Modal>

      <DetailDrawer isOpen={!!detailTarget} onClose={() => setDetailTarget(null)} title={detailTarget?.letter_number || "Detail Surat"}>
        {detailTarget && (
          <dl>
            <DetailField label="Nomor Surat" value={detailTarget.letter_number} />
            <DetailField label="Perihal" value={detailTarget.subject} />
            <DetailField label="Karyawan" value={employeeName(detailTarget.employee_id)} />
            <DetailField label="Tanggal Terbit" value={new Date(detailTarget.issue_date).toLocaleDateString()} />
            <DetailField
              label="File"
              value={detailTarget.file_url ? <a href={detailTarget.file_url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline">Buka File</a> : null}
            />
          </dl>
        )}
      </DetailDrawer>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        message={`Hapus surat "${deleteTarget?.letter_number}"?`}
        isConfirming={deleteMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};

export default InternalDocumentPage;
