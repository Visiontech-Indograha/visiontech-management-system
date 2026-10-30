import { createContext, useContext } from "react";

/**
 * Penjaga tutup dialog formulir. `VmsDialog` menyediakannya ke seluruh isi dialog (termasuk footer):
 * bila formulir berubah (dirty), aksi tutup/Batal ditahan dan konfirmasi "Tutup tanpa menyimpan?" diminta dulu.
 * Di luar VmsDialog, aksi langsung dijalankan.
 */
export type DialogGuard = (next: () => void) => void;

export const DialogGuardContext = createContext<DialogGuard>((next) => next());

export function useDialogGuard(): DialogGuard {
  return useContext(DialogGuardContext);
}
