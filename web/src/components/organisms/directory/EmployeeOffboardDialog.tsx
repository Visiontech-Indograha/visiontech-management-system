import { OffboardingFormDialog } from "@/components/organisms/offboarding/OffboardingFormDialog";
import type { Employee } from "@/services/employeeService";

/**
 * HR memulai offboarding dari detail karyawan (Milestone 9, docs/35 §7). Masa kerja baru berakhir setelah
 * clearance aset lengkap, PM & HR menyetujui, dan tanggal efektif tiba — dikelola di menu Offboarding.
 */
export function EmployeeOffboardDialog({ employee, onClose }: { employee: Employee; onClose: () => void }) {
  return <OffboardingFormDialog employee={{ id: employee.id, name: employee.full_name }} onClose={onClose} />;
}
