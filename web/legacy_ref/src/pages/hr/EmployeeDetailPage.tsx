import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useEmployee,
  useUpdateEmployee,
  useSaveIdCard,
  useDeleteIdCard,
  useSaveBpjs,
  useDeleteBpjs,
  useAddDrivingCard,
  useUpdateDrivingCard,
  useDeleteDrivingCard,
  useAddCertificate,
  useUpdateCertificate,
  useDeleteCertificate,
} from "../../hooks/api/useEmployees";
import { useTitles } from "../../hooks/api/useMaster";
import { EMPTY_EMPLOYEE_FORM, EmployeeFormValues, EmployeeResponse } from "../../types/hr";
import { Button } from "../../components/ui/Button";
import { Input, Select } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { LoadingState, ErrorState } from "../../components/ui/QueryState";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";

function toFormValues(emp: EmployeeResponse): EmployeeFormValues {
  return {
    ...EMPTY_EMPLOYEE_FORM,
    nik: emp.nik,
    full_name: emp.full_name,
    email: emp.email || "",
    phone_number: emp.phone_number || "",
    join_date: emp.join_date || "",
    is_active: emp.is_active,
    title_id: emp.title_id || "",
    gender: emp.gender || "",
    birth_place: emp.birth_place || "",
    birth_date: emp.birth_date || "",
    marital_status: emp.marital_status || "",
    religion: emp.religion || "",
    address: emp.address || "",
    last_education: emp.last_education || "",
    employment_status: emp.employment_status || "",
    department: emp.department || "",
    contract_number: emp.contract_number || "",
    contract_start: emp.contract_start || "",
    contract_end: emp.contract_end || "",
    emergency_contact_name: emp.emergency_contact_name || "",
    emergency_contact_phone: emp.emergency_contact_phone || "",
    bank_name: emp.bank_name || "",
    bank_account_number: emp.bank_account_number || "",
    npwp: emp.npwp || "",
  };
}

function cleanPayload<T extends object>(form: T): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(form)) {
    if (value === "") continue;
    payload[key] = value;
  }
  return payload;
}

const Field = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div>
    <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</dt>
    <dd className="mt-0.5 text-sm text-gray-900">{value || "-"}</dd>
  </div>
);

const EmployeeDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const { data: emp, isLoading, error } = useEmployee(id);
  const { data: titles } = useTitles();
  const updateEmp = useUpdateEmployee(id!);
  const { user } = useAuth();
  const canWrite = user?.role === UserRole.ADMIN || user?.role === UserRole.HR_HES;

  const [tab, setTab] = useState<"profil" | "dokumen">("profil");
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [form, setForm] = useState<EmployeeFormValues>(EMPTY_EMPLOYEE_FORM);

  if (isLoading) return <LoadingState label="Memuat profil karyawan..." />;
  if (error || !emp) return <ErrorState label="Karyawan tidak ditemukan." />;

  const titleName = titles?.find((t) => t.id === emp.title_id)?.name;

  const openEdit = () => {
    setForm(toFormValues(emp));
    setIsEditOpen(true);
  };

  const setField = <K extends keyof EmployeeFormValues>(key: K, value: EmployeeFormValues[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await updateEmp.mutateAsync(cleanPayload(form));
    setIsEditOpen(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <Link to="/hr/employees" className="text-sm text-indigo-600 hover:underline">&larr; Kembali ke Daftar Karyawan</Link>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-gray-200 bg-white p-6 shadow">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{emp.full_name}</h1>
          <p className="text-sm text-gray-500">{emp.nik} {titleName ? `· ${titleName}` : ""}</p>
          <div className="mt-2 flex gap-2">
            {emp.is_active ? (
              <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800">Aktif</span>
            ) : (
              <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">Nonaktif</span>
            )}
            {emp.employment_status && (
              <span className="inline-flex rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-800">
                {emp.employment_status}
              </span>
            )}
          </div>
        </div>
        {canWrite && <Button onClick={openEdit}>Edit Profil</Button>}
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {(["profil", "dokumen"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`${tab === t ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"} whitespace-nowrap border-b-2 px-1 pb-4 text-sm font-medium capitalize`}
            >
              {t === "profil" ? "Profil" : "Dokumen"}
            </button>
          ))}
        </nav>
      </div>

      {tab === "profil" && (
        <div className="space-y-6">
          <section className="rounded-lg border border-gray-200 bg-white p-6 shadow">
            <h2 className="mb-4 text-sm font-semibold uppercase text-gray-500">Data Pribadi</h2>
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="Email" value={emp.email} />
              <Field label="No. Telepon" value={emp.phone_number} />
              <Field label="Jenis Kelamin" value={emp.gender} />
              <Field label="Tempat, Tanggal Lahir" value={emp.birth_place || emp.birth_date ? `${emp.birth_place || "-"}, ${emp.birth_date || "-"}` : null} />
              <Field label="Status Pernikahan" value={emp.marital_status} />
              <Field label="Agama" value={emp.religion} />
              <Field label="Pendidikan Terakhir" value={emp.last_education} />
              <Field label="Alamat" value={emp.address} />
            </dl>
          </section>

          <section className="rounded-lg border border-gray-200 bg-white p-6 shadow">
            <h2 className="mb-4 text-sm font-semibold uppercase text-gray-500">Kepegawaian</h2>
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="Jabatan" value={titleName} />
              <Field label="Departemen" value={emp.department} />
              <Field label="Tanggal Bergabung" value={emp.join_date} />
              <Field label="Status Kepegawaian" value={emp.employment_status} />
              {emp.employment_status === "KONTRAK" && (
                <>
                  <Field label="Nomor PKWT" value={emp.contract_number} />
                  <Field label="Masa Kontrak" value={emp.contract_start || emp.contract_end ? `${emp.contract_start || "-"} s/d ${emp.contract_end || "-"}` : null} />
                </>
              )}
            </dl>
          </section>

          <section className="rounded-lg border border-gray-200 bg-white p-6 shadow">
            <h2 className="mb-4 text-sm font-semibold uppercase text-gray-500">Kontak Darurat & Keuangan</h2>
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="Kontak Darurat" value={emp.emergency_contact_name} />
              <Field label="No. Telepon Darurat" value={emp.emergency_contact_phone} />
              <Field label="Bank" value={emp.bank_name} />
              <Field label="No. Rekening" value={emp.bank_account_number} />
              <Field label="NPWP" value={emp.npwp} />
            </dl>
          </section>
        </div>
      )}

      {tab === "dokumen" && <DocumentsTab employeeId={emp.id} employee={emp} canWrite={canWrite} />}

      <Modal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} title="Edit Profil Karyawan" size="lg">
        <form onSubmit={handleSave} className="space-y-6">
          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-500 uppercase">Identitas</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input label="Nama Lengkap" required value={form.full_name} onChange={(e) => setField("full_name", e.target.value)} />
              <Input label="Email" type="email" value={form.email} onChange={(e) => setField("email", e.target.value)} />
              <Input label="No. Telepon" value={form.phone_number} onChange={(e) => setField("phone_number", e.target.value)} />
              <Select label="Jenis Kelamin" value={form.gender} onChange={(e) => setField("gender", e.target.value as EmployeeFormValues["gender"])}>
                <option value="">-- Pilih --</option>
                <option value="PRIA">Pria</option>
                <option value="WANITA">Wanita</option>
              </Select>
              <Input label="Tempat Lahir" value={form.birth_place} onChange={(e) => setField("birth_place", e.target.value)} />
              <Input label="Tanggal Lahir" type="date" value={form.birth_date} onChange={(e) => setField("birth_date", e.target.value)} />
              <Input label="Status Pernikahan" value={form.marital_status} onChange={(e) => setField("marital_status", e.target.value)} />
              <Input label="Agama" value={form.religion} onChange={(e) => setField("religion", e.target.value)} />
              <Input label="Pendidikan Terakhir" value={form.last_education} onChange={(e) => setField("last_education", e.target.value)} />
            </div>
            <Input label="Alamat" value={form.address} onChange={(e) => setField("address", e.target.value)} />
          </section>

          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-500 uppercase">Kepegawaian</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Select label="Jabatan" value={form.title_id} onChange={(e) => setField("title_id", e.target.value)}>
                <option value="">-- Tidak Ada --</option>
                {titles?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </Select>
              <Input label="Departemen" value={form.department} onChange={(e) => setField("department", e.target.value)} />
              <Input label="Tanggal Bergabung" type="date" value={form.join_date} onChange={(e) => setField("join_date", e.target.value)} />
              <Select label="Status Kepegawaian" value={form.employment_status} onChange={(e) => setField("employment_status", e.target.value as EmployeeFormValues["employment_status"])}>
                <option value="">-- Pilih --</option>
                <option value="TETAP">Tetap</option>
                <option value="KONTRAK">Kontrak</option>
              </Select>
              <Select label="Status Aktif" value={form.is_active ? "1" : "0"} onChange={(e) => setField("is_active", e.target.value === "1")}>
                <option value="1">Aktif</option>
                <option value="0">Nonaktif</option>
              </Select>
              {form.employment_status === "KONTRAK" && (
                <>
                  <Input label="Nomor PKWT" value={form.contract_number} onChange={(e) => setField("contract_number", e.target.value)} />
                  <Input label="Mulai Kontrak" type="date" value={form.contract_start} onChange={(e) => setField("contract_start", e.target.value)} />
                  <Input label="Berakhir Kontrak" type="date" value={form.contract_end} onChange={(e) => setField("contract_end", e.target.value)} />
                </>
              )}
            </div>
          </section>

          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-500 uppercase">Kontak Darurat & Keuangan</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input label="Nama Kontak Darurat" value={form.emergency_contact_name} onChange={(e) => setField("emergency_contact_name", e.target.value)} />
              <Input label="No. Telepon Darurat" value={form.emergency_contact_phone} onChange={(e) => setField("emergency_contact_phone", e.target.value)} />
              <Input label="Nama Bank" value={form.bank_name} onChange={(e) => setField("bank_name", e.target.value)} />
              <Input label="No. Rekening" value={form.bank_account_number} onChange={(e) => setField("bank_account_number", e.target.value)} />
              <Input label="NPWP" value={form.npwp} onChange={(e) => setField("npwp", e.target.value)} />
            </div>
          </section>

          <ModalFooter onCancel={() => setIsEditOpen(false)} isSubmitting={updateEmp.isPending} />
        </form>
      </Modal>
    </div>
  );
};

// ==================== Tab Dokumen ====================

const DocumentsTab = ({ employeeId, employee, canWrite }: { employeeId: string; employee: EmployeeResponse; canWrite: boolean }) => {
  return (
    <div className="space-y-6">
      <IdCardSection employeeId={employeeId} idCard={employee.id_card} canWrite={canWrite} />
      <BpjsSection employeeId={employeeId} bpjs={employee.bpjs} canWrite={canWrite} />
      <DrivingCardSection employeeId={employeeId} cards={employee.driving_cards} canWrite={canWrite} />
      <CertificateSection employeeId={employeeId} certs={employee.certificates} canWrite={canWrite} />
    </div>
  );
};

const SectionShell = ({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) => (
  <section className="rounded-lg border border-gray-200 bg-white p-6 shadow">
    <div className="mb-4 flex items-center justify-between">
      <h2 className="text-sm font-semibold uppercase text-gray-500">{title}</h2>
      {action}
    </div>
    {children}
  </section>
);

const IdCardSection = ({ employeeId, idCard, canWrite }: { employeeId: string; idCard: EmployeeResponse["id_card"]; canWrite: boolean }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [form, setForm] = useState({ card_number: "", card_type: "KTP", religion: "", gender: "", blood_type: "", address: "", city: "" });
  const save = useSaveIdCard(employeeId);
  const del = useDeleteIdCard(employeeId);

  const open = () => {
    setForm({
      card_number: idCard?.card_number || "",
      card_type: idCard?.card_type || "KTP",
      religion: idCard?.religion || "",
      gender: idCard?.gender || "",
      blood_type: idCard?.blood_type || "",
      address: idCard?.address || "",
      city: idCard?.city || "",
    });
    setIsOpen(true);
  };

  return (
    <SectionShell title="KTP" action={canWrite && <Button onClick={open}>{idCard ? "Edit" : "Tambah"} KTP</Button>}>
      {idCard ? (
        <div className="flex items-start justify-between">
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
            <Field label="No. KTP" value={idCard.card_number} />
            <Field label="Gender" value={idCard.gender} />
            <Field label="Golongan Darah" value={idCard.blood_type} />
            <Field label="Kota" value={idCard.city} />
            <Field label="Alamat" value={idCard.address} />
          </dl>
          {canWrite && <button onClick={() => setConfirmDelete(true)} className="text-sm text-red-600 hover:underline">Hapus</button>}
        </div>
      ) : (
        <p className="text-sm text-gray-400">Belum ada data KTP.</p>
      )}

      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="KTP">
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            await save.mutateAsync({ payload: form, exists: !!idCard });
            setIsOpen(false);
          }}
          className="space-y-4"
        >
          <Input label="No. KTP" required value={form.card_number} onChange={(e) => setForm({ ...form, card_number: e.target.value })} />
          <Select label="Jenis Kelamin" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
            <option value="">-- Pilih --</option>
            <option value="Laki-laki">Laki-laki</option>
            <option value="Perempuan">Perempuan</option>
          </Select>
          <Input label="Golongan Darah" value={form.blood_type} onChange={(e) => setForm({ ...form, blood_type: e.target.value })} />
          <Input label="Kota" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          <Input label="Alamat (sesuai KTP)" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          <ModalFooter onCancel={() => setIsOpen(false)} isSubmitting={save.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={confirmDelete}
        message="Hapus data KTP karyawan ini?"
        isConfirming={del.isPending}
        onConfirm={async () => { await del.mutateAsync(); setConfirmDelete(false); }}
        onCancel={() => setConfirmDelete(false)}
      />
    </SectionShell>
  );
};

const BpjsSection = ({ employeeId, bpjs, canWrite }: { employeeId: string; bpjs: EmployeeResponse["bpjs"]; canWrite: boolean }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [form, setForm] = useState({ kesehatan_number: "", ketenagakerjaan_number: "" });
  const save = useSaveBpjs(employeeId);
  const del = useDeleteBpjs(employeeId);

  const open = () => {
    setForm({ kesehatan_number: bpjs?.kesehatan_number || "", ketenagakerjaan_number: bpjs?.ketenagakerjaan_number || "" });
    setIsOpen(true);
  };

  return (
    <SectionShell title="BPJS" action={canWrite && <Button onClick={open}>{bpjs ? "Edit" : "Tambah"} BPJS</Button>}>
      {bpjs ? (
        <div className="flex items-start justify-between">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Field label="No. BPJS Kesehatan" value={bpjs.kesehatan_number} />
            <Field label="No. BPJS Ketenagakerjaan" value={bpjs.ketenagakerjaan_number} />
          </dl>
          {canWrite && <button onClick={() => setConfirmDelete(true)} className="text-sm text-red-600 hover:underline">Hapus</button>}
        </div>
      ) : (
        <p className="text-sm text-gray-400">Belum ada data BPJS.</p>
      )}

      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="BPJS">
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            await save.mutateAsync({ payload: form, exists: !!bpjs });
            setIsOpen(false);
          }}
          className="space-y-4"
        >
          <Input label="No. BPJS Kesehatan" value={form.kesehatan_number} onChange={(e) => setForm({ ...form, kesehatan_number: e.target.value })} />
          <Input label="No. BPJS Ketenagakerjaan" value={form.ketenagakerjaan_number} onChange={(e) => setForm({ ...form, ketenagakerjaan_number: e.target.value })} />
          <ModalFooter onCancel={() => setIsOpen(false)} isSubmitting={save.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={confirmDelete}
        message="Hapus data BPJS karyawan ini?"
        isConfirming={del.isPending}
        onConfirm={async () => { await del.mutateAsync(); setConfirmDelete(false); }}
        onCancel={() => setConfirmDelete(false)}
      />
    </SectionShell>
  );
};

const DrivingCardSection = ({ employeeId, cards, canWrite }: { employeeId: string; cards: EmployeeResponse["driving_cards"]; canWrite: boolean }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [form, setForm] = useState({ card_type: "", card_number: "", expire_date: "" });
  const add = useAddDrivingCard(employeeId);
  const update = useUpdateDrivingCard(employeeId);
  const del = useDeleteDrivingCard(employeeId);

  const openNew = () => { setEditingId(null); setForm({ card_type: "", card_number: "", expire_date: "" }); setIsOpen(true); };
  const openEdit = (card: EmployeeResponse["driving_cards"][number]) => {
    setEditingId(card.id);
    setForm({ card_type: card.card_type, card_number: card.card_number, expire_date: card.expire_date });
    setIsOpen(true);
  };

  return (
    <SectionShell title="SIM / SIO" action={canWrite && <Button onClick={openNew}>Tambah SIM/SIO</Button>}>
      {cards.length === 0 ? (
        <p className="text-sm text-gray-400">Belum ada data SIM/SIO.</p>
      ) : (
        <ul className="divide-y divide-gray-100">
          {cards.map((c) => (
            <li key={c.id} className="flex items-center justify-between py-2 text-sm">
              <span>{c.card_type} — {c.card_number} (exp. {c.expire_date})</span>
              {canWrite && (
                <div className="space-x-3">
                  <button onClick={() => openEdit(c)} className="text-indigo-600 hover:underline">Edit</button>
                  <button onClick={() => setDeleteId(c.id)} className="text-red-600 hover:underline">Hapus</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title={editingId ? "Edit SIM/SIO" : "Tambah SIM/SIO"}>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (editingId) await update.mutateAsync({ cardId: editingId, payload: form });
            else await add.mutateAsync(form);
            setIsOpen(false);
          }}
          className="space-y-4"
        >
          <Input label="Tipe (SIM A/SIM C/SIO)" required value={form.card_type} onChange={(e) => setForm({ ...form, card_type: e.target.value })} />
          <Input label="Nomor" required value={form.card_number} onChange={(e) => setForm({ ...form, card_number: e.target.value })} />
          <Input label="Tanggal Kedaluwarsa" type="date" required value={form.expire_date} onChange={(e) => setForm({ ...form, expire_date: e.target.value })} />
          <ModalFooter onCancel={() => setIsOpen(false)} isSubmitting={add.isPending || update.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleteId}
        message="Hapus data SIM/SIO ini?"
        isConfirming={del.isPending}
        onConfirm={async () => { if (deleteId) await del.mutateAsync(deleteId); setDeleteId(null); }}
        onCancel={() => setDeleteId(null)}
      />
    </SectionShell>
  );
};

const CertificateSection = ({ employeeId, certs, canWrite }: { employeeId: string; certs: EmployeeResponse["certificates"]; canWrite: boolean }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [form, setForm] = useState({ certificate_name: "", certificate_number: "", issuer: "", issue_date: "", expire_date: "" });
  const add = useAddCertificate(employeeId);
  const update = useUpdateCertificate(employeeId);
  const del = useDeleteCertificate(employeeId);

  const openNew = () => { setEditingId(null); setForm({ certificate_name: "", certificate_number: "", issuer: "", issue_date: "", expire_date: "" }); setIsOpen(true); };
  const openEdit = (cert: EmployeeResponse["certificates"][number]) => {
    setEditingId(cert.id);
    setForm({
      certificate_name: cert.certificate_name,
      certificate_number: cert.certificate_number || "",
      issuer: cert.issuer || "",
      issue_date: cert.issue_date || "",
      expire_date: cert.expire_date || "",
    });
    setIsOpen(true);
  };

  return (
    <SectionShell title="Sertifikat" action={canWrite && <Button onClick={openNew}>Tambah Sertifikat</Button>}>
      {certs.length === 0 ? (
        <p className="text-sm text-gray-400">Belum ada sertifikat.</p>
      ) : (
        <ul className="divide-y divide-gray-100">
          {certs.map((c) => (
            <li key={c.id} className="flex items-center justify-between py-2 text-sm">
              <span>{c.certificate_name} {c.issuer ? `— ${c.issuer}` : ""} {c.expire_date ? `(exp. ${c.expire_date})` : ""}</span>
              {canWrite && (
                <div className="space-x-3">
                  <button onClick={() => openEdit(c)} className="text-indigo-600 hover:underline">Edit</button>
                  <button onClick={() => setDeleteId(c.id)} className="text-red-600 hover:underline">Hapus</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title={editingId ? "Edit Sertifikat" : "Tambah Sertifikat"}>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const payload = cleanPayload(form);
            if (editingId) await update.mutateAsync({ cardId: editingId, payload });
            else await add.mutateAsync(payload);
            setIsOpen(false);
          }}
          className="space-y-4"
        >
          <Input label="Nama Sertifikat" required value={form.certificate_name} onChange={(e) => setForm({ ...form, certificate_name: e.target.value })} />
          <Input label="Nomor Sertifikat" value={form.certificate_number} onChange={(e) => setForm({ ...form, certificate_number: e.target.value })} />
          <Input label="Penerbit" value={form.issuer} onChange={(e) => setForm({ ...form, issuer: e.target.value })} />
          <Input label="Tanggal Terbit" type="date" value={form.issue_date} onChange={(e) => setForm({ ...form, issue_date: e.target.value })} />
          <Input label="Tanggal Kedaluwarsa" type="date" value={form.expire_date} onChange={(e) => setForm({ ...form, expire_date: e.target.value })} />
          <ModalFooter onCancel={() => setIsOpen(false)} isSubmitting={add.isPending || update.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleteId}
        message="Hapus sertifikat ini?"
        isConfirming={del.isPending}
        onConfirm={async () => { if (deleteId) await del.mutateAsync(deleteId); setDeleteId(null); }}
        onCancel={() => setDeleteId(null)}
      />
    </SectionShell>
  );
};

export default EmployeeDetailPage;
