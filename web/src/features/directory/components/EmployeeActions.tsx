import { Button } from "@/components/atoms/Button";

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
                <Button variant="outline" onClick={onPromote}>
                  Mutasi / promosi
                </Button>
              )}
              {isActive && (
                <Button variant="outline" onClick={onOffboard}>
                  Offboarding
                </Button>
              )}
              <Button variant="outline" onClick={onEdit}>
                Ubah profil
              </Button>
            </div>
  );
}
