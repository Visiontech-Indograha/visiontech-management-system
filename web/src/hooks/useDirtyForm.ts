import { useCallback, useState } from "react";

/**
 * Formulir tanpa react-hook-form: `dirty` menjadi true begitu ada isian yang diubah.
 * Pasang `formProps` pada `<FormBlock>` dan `dirty` pada `<VmsDialog>` agar klik luar/Esc
 * meminta konfirmasi sebelum perubahan dibuang (pola LeaveApplyDialog).
 */
export function useDirtyForm() {
  const [dirty, setDirty] = useState(false);
  const mark = useCallback(() => setDirty(true), []);
  return { dirty, formProps: { onChange: mark, onInput: mark } };
}
