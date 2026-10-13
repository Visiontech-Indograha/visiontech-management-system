import { ActionButton } from "@/components/molecules/ActionButton";

/** Aksi HR di kepala halaman detail karyawan: mutasi/promosi & offboarding (hanya karyawan aktif), ubah profil. */
export function EmployeeActions({ isActive, onPromote, onOffboard, onEdit }: {
  isActive: boolean;
  onPromote: () => void;
  onOffboard: () => void;
  onEdit: () => void;
}) {
  return (
            <div className="flex flex-wrap gap-2">
              {isActive && (
                <ActionButton variant="outline" onClick={onPromote}>
                  Mutasi / promosi
                </ActionButton>
              )}
              {isActive && (
                <ActionButton variant="outline" onClick={onOffboard}>
                  Offboarding
                </ActionButton>
              )}
              <ActionButton variant="outline" onClick={onEdit}>
                Ubah profil
              </ActionButton>
            </div>
  );
}
