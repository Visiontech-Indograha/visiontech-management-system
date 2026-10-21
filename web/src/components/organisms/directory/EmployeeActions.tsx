import { ActionButton } from "@/components/molecules/ActionButton";

/** Aksi HR di kepala halaman detail karyawan: offboarding (hanya karyawan aktif) & ubah data. */
export function EmployeeActions({ isActive, onOffboard, onEdit }: {
  isActive: boolean;
  onOffboard: () => void;
  onEdit: () => void;
}) {
  return (
            <div className="flex flex-wrap gap-2">
              {isActive && (
                <ActionButton variant="outline" onClick={onOffboard}>
                  Offboarding
                </ActionButton>
              )}
              <ActionButton variant="outline" onClick={onEdit}>
                Ubah data
              </ActionButton>
            </div>
  );
}
