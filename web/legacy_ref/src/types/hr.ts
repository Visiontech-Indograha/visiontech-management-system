export interface IDCardResponse {
  id: string;
  employee_id: string;
  card_number: string;
  card_type: string;
  religion: string | null;
  gender: string | null;
  blood_type: string | null;
  address: string | null;
  city: string | null;
  expire_date: string | null;
  attachment_url: string | null;
}

export interface BPJSResponse {
  id: string;
  employee_id: string;
  kesehatan_number: string | null;
  ketenagakerjaan_number: string | null;
  attachment_url: string | null;
}

export interface DrivingCardResponse {
  id: string;
  employee_id: string;
  card_type: string;
  card_number: string;
  expire_date: string;
  attachment_url: string | null;
}

export interface CertificateEmpResponse {
  id: string;
  employee_id: string;
  certificate_name: string;
  certificate_number: string | null;
  issuer: string | null;
  issue_date: string | null;
  expire_date: string | null;
  attachment_url: string | null;
}

export type Gender = "PRIA" | "WANITA";
export type EmploymentStatus = "TETAP" | "KONTRAK";

export interface EmployeeResponse {
  id: string;
  nik: string;
  full_name: string;
  email: string | null;
  phone_number: string | null;
  join_date: string | null;
  is_active: boolean;
  title_id: string | null;

  // Data pribadi
  gender: Gender | null;
  birth_place: string | null;
  birth_date: string | null;
  marital_status: string | null;
  religion: string | null;
  address: string | null;
  last_education: string | null;

  // Kepegawaian
  employment_status: EmploymentStatus | null;
  department: string | null;
  contract_number: string | null;
  contract_start: string | null;
  contract_end: string | null;

  // Kontak darurat
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;

  // Keuangan
  bank_name: string | null;
  bank_account_number: string | null;
  npwp: string | null;

  // Relasi bersarang
  id_card: IDCardResponse | null;
  bpjs: BPJSResponse | null;
  driving_cards: DrivingCardResponse[];
  certificates: CertificateEmpResponse[];
}

/** Payload create/update — semua field opsional kecuali nik/full_name saat create. */
export interface EmployeeFormValues {
  nik: string;
  full_name: string;
  email: string;
  phone_number: string;
  join_date: string;
  is_active: boolean;
  title_id: string;
  gender: Gender | "";
  birth_place: string;
  birth_date: string;
  marital_status: string;
  religion: string;
  address: string;
  last_education: string;
  employment_status: EmploymentStatus | "";
  department: string;
  contract_number: string;
  contract_start: string;
  contract_end: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  bank_name: string;
  bank_account_number: string;
  npwp: string;
}

export const EMPTY_EMPLOYEE_FORM: EmployeeFormValues = {
  nik: "",
  full_name: "",
  email: "",
  phone_number: "",
  join_date: "",
  is_active: true,
  title_id: "",
  gender: "",
  birth_place: "",
  birth_date: "",
  marital_status: "",
  religion: "",
  address: "",
  last_education: "",
  employment_status: "",
  department: "",
  contract_number: "",
  contract_start: "",
  contract_end: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  bank_name: "",
  bank_account_number: "",
  npwp: "",
};
