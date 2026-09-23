import { useState } from "react";
import { Link } from "react-router-dom";
import {
  useEmployees,
  useCreateEmployee,
  useCreateUserAccount,
  useDeleteEmployee,
} from "../../hooks/api/useEmployees";
import { useTitles } from "../../hooks/api/useMaster";
import { EMPTY_EMPLOYEE_FORM, EmployeeFormValues } from "../../types/hr";
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from "../../components/ui/Table";
import { Button } from "../../components/ui/Button";
import { Input, Select } from "../../components/ui/Input";
import { Modal, ModalFooter } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { SearchBar } from "../../components/ui/SearchBar";
import { Pagination } from "../../components/ui/Pagination";
import { LoadingState, ErrorState, EmptyTableRow } from "../../components/ui/QueryState";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useAuth } from "../../contexts/AuthContext";
import { UserRole } from "../../types/auth";

const PAGE_SIZE = 20;

/** Buang field kosong ("") sebelum dikirim — biar backend terima `null`/tidak-diisi, bukan string kosong. */
function cleanPayload(form: EmployeeFormValues): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(form)) {
    if (value === "" || value === undefined) continue;
    payload[key] = value;
  }
  return payload;
}

const EmployeeListPage = () => {
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput);
  const [skip, setSkip] = useState(0);

  const { data: employees, isLoading, error } = useEmployees({ q: search || undefined, skip, limit: PAGE_SIZE });
  const { data: titles } = useTitles();
  const { user } = useAuth();
  const canWrite = user?.role === UserRole.ADMIN || user?.role === UserRole.HR_HES;
  const createEmp = useCreateEmployee();
  const createUser = useCreateUserAccount();
  const deleteEmp = useDeleteEmployee();

  const [isEmpModalOpen, setIsEmpModalOpen] = useState(false);
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [selectedEmpId, setSelectedEmpId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  const [empForm, setEmpForm] = useState<EmployeeFormValues>(EMPTY_EMPLOYEE_FORM);
  const [userForm, setUserForm] = useState({ username: "", password: "", role: "FIELD_STAFF" });

  const setField = <K extends keyof EmployeeFormValues>(key: K, value: EmployeeFormValues[K]) =>
    setEmpForm((f) => ({ ...f, [key]: value }));

  if (isLoading) {
    return <LoadingState label="Loading daftar karyawan..." />;
  }

  if (error || !employees) {
    return <ErrorState label="Gagal memuat data karyawan." />;
  }

  const handleCreateEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    await createEmp.mutateAsync(cleanPayload(empForm));
    setIsEmpModalOpen(false);
    setEmpForm(EMPTY_EMPLOYEE_FORM);
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEmpId) return;
    await createUser.mutateAsync({ ...userForm, employee_id: selectedEmpId });
    setIsUserModalOpen(false);
    setUserForm({ username: "", password: "", role: "FIELD_STAFF" });
    setSelectedEmpId(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteEmp.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  return (
    <div className="space-y-6">
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Daftar Karyawan</h1>
          <p className="mt-1 text-sm text-gray-500">
            Kelola data profil dan dokumen karyawan.
          </p>
        </div>
        {canWrite && (
          <div className="mt-4 sm:mt-0">
            <Button onClick={() => setIsEmpModalOpen(true)}>Tambah Karyawan</Button>
          </div>
        )}
      </div>

      <SearchBar value={searchInput} onChange={(v) => { setSearchInput(v); setSkip(0); }} placeholder="Cari berdasarkan nama, NIK, email, atau departemen..." />

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>NIK</TableHeader>
              <TableHeader>Nama Lengkap</TableHeader>
              <TableHeader>Jabatan</TableHeader>
              <TableHeader>Status</TableHeader>
              <TableHeader>Kepegawaian</TableHeader>
              <TableHeader>Aksi</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {employees.length === 0 ? (
              <EmptyTableRow colSpan={6} label="Data tidak ditemukan." />
            ) : (
              employees.map((emp) => (
                <TableRow key={emp.id}>
                  <TableCell><span className="font-medium text-gray-900">{emp.nik}</span></TableCell>
                  <TableCell>
                    <Link to={`/hr/employees/${emp.id}`} className="text-indigo-600 hover:underline">
                      {emp.full_name}
                    </Link>
                  </TableCell>
                  <TableCell>{titles?.find((t) => t.id === emp.title_id)?.name || "-"}</TableCell>
                  <TableCell>
                    {emp.is_active ? (
                      <span className="inline-flex rounded-full bg-green-100 px-2 text-xs font-semibold text-green-800">Aktif</span>
                    ) : (
                      <span className="inline-flex rounded-full bg-red-100 px-2 text-xs font-semibold text-red-800">Nonaktif</span>
                    )}
                  </TableCell>
                  <TableCell>{emp.employment_status || "-"}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-3">
                      <Link to={`/hr/employees/${emp.id}`} className="text-indigo-600 hover:underline text-sm">
                        Detail
                      </Link>
                      {canWrite && (
                        <>
                          <button
                            onClick={() => { setSelectedEmpId(emp.id); setIsUserModalOpen(true); }}
                            className="text-indigo-600 hover:underline text-sm"
                          >
                            Buat Akun
                          </button>
                          <button
                            onClick={() => setDeleteTarget({ id: emp.id, name: emp.full_name })}
                            className="text-red-600 hover:underline text-sm"
                          >
                            Hapus
                          </button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <Pagination skip={skip} limit={PAGE_SIZE} currentCount={employees.length} onSkipChange={setSkip} />
      </div>

      <Modal isOpen={isEmpModalOpen} onClose={() => setIsEmpModalOpen(false)} title="Tambah Karyawan" size="lg">
        <form onSubmit={handleCreateEmployee} className="space-y-6">
          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-500 uppercase">Identitas</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input label="NIK" required value={empForm.nik} onChange={(e) => setField("nik", e.target.value)} />
              <Input label="Nama Lengkap" required value={empForm.full_name} onChange={(e) => setField("full_name", e.target.value)} />
              <Input label="Email" type="email" value={empForm.email} onChange={(e) => setField("email", e.target.value)} />
              <Input label="No. Telepon" value={empForm.phone_number} onChange={(e) => setField("phone_number", e.target.value)} />
              <Select label="Jenis Kelamin" value={empForm.gender} onChange={(e) => setField("gender", e.target.value as EmployeeFormValues["gender"])}>
                <option value="">-- Pilih --</option>
                <option value="PRIA">Pria</option>
                <option value="WANITA">Wanita</option>
              </Select>
              <Input label="Tempat Lahir" value={empForm.birth_place} onChange={(e) => setField("birth_place", e.target.value)} />
              <Input label="Tanggal Lahir" type="date" value={empForm.birth_date} onChange={(e) => setField("birth_date", e.target.value)} />
              <Input label="Status Pernikahan" value={empForm.marital_status} onChange={(e) => setField("marital_status", e.target.value)} placeholder="LAJANG / MENIKAH / CERAI" />
              <Input label="Agama" value={empForm.religion} onChange={(e) => setField("religion", e.target.value)} />
              <Input label="Pendidikan Terakhir" value={empForm.last_education} onChange={(e) => setField("last_education", e.target.value)} placeholder="SMA / D3 / S1 / S2" />
            </div>
            <Input label="Alamat" value={empForm.address} onChange={(e) => setField("address", e.target.value)} />
          </section>

          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-500 uppercase">Kepegawaian</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Select label="Jabatan" value={empForm.title_id} onChange={(e) => setField("title_id", e.target.value)}>
                <option value="">-- Tidak Ada --</option>
                {titles?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </Select>
              <Input label="Departemen" value={empForm.department} onChange={(e) => setField("department", e.target.value)} />
              <Input label="Tanggal Bergabung" type="date" value={empForm.join_date} onChange={(e) => setField("join_date", e.target.value)} />
              <Select label="Status Kepegawaian" value={empForm.employment_status} onChange={(e) => setField("employment_status", e.target.value as EmployeeFormValues["employment_status"])}>
                <option value="">-- Pilih --</option>
                <option value="TETAP">Tetap</option>
                <option value="KONTRAK">Kontrak</option>
              </Select>
              {empForm.employment_status === "KONTRAK" && (
                <>
                  <Input label="Nomor PKWT" value={empForm.contract_number} onChange={(e) => setField("contract_number", e.target.value)} />
                  <Input label="Mulai Kontrak" type="date" value={empForm.contract_start} onChange={(e) => setField("contract_start", e.target.value)} />
                  <Input label="Berakhir Kontrak" type="date" value={empForm.contract_end} onChange={(e) => setField("contract_end", e.target.value)} />
                </>
              )}
            </div>
          </section>

          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-500 uppercase">Kontak Darurat & Keuangan</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input label="Nama Kontak Darurat" value={empForm.emergency_contact_name} onChange={(e) => setField("emergency_contact_name", e.target.value)} />
              <Input label="No. Telepon Darurat" value={empForm.emergency_contact_phone} onChange={(e) => setField("emergency_contact_phone", e.target.value)} />
              <Input label="Nama Bank" value={empForm.bank_name} onChange={(e) => setField("bank_name", e.target.value)} />
              <Input label="No. Rekening" value={empForm.bank_account_number} onChange={(e) => setField("bank_account_number", e.target.value)} />
              <Input label="NPWP" value={empForm.npwp} onChange={(e) => setField("npwp", e.target.value)} />
            </div>
          </section>

          <ModalFooter onCancel={() => setIsEmpModalOpen(false)} isSubmitting={createEmp.isPending} />
        </form>
      </Modal>

      <Modal isOpen={isUserModalOpen} onClose={() => setIsUserModalOpen(false)} title="Buat Akun Login">
        <form onSubmit={handleCreateUser} className="space-y-4">
          <Input
            label="Username"
            required
            value={userForm.username}
            onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
          />
          <Input
            label="Password"
            required
            type="password"
            value={userForm.password}
            onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
          />
          <Select
            label="Role"
            value={userForm.role}
            onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
          >
            <option value="FIELD_STAFF">Field Staff</option>
            <option value="PM">Project Manager</option>
            <option value="OM">Operational Manager</option>
            <option value="FINANCE">Finance</option>
            <option value="HR_HES">HR / HES</option>
            <option value="ADMIN">Admin</option>
          </Select>
          <ModalFooter onCancel={() => setIsUserModalOpen(false)} isSubmitting={createUser.isPending} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        message={`Hapus data karyawan "${deleteTarget?.name}"? Data dokumen terkait akan tetap tersimpan untuk audit.`}
        isConfirming={deleteEmp.isPending}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

export default EmployeeListPage;
