import type { ComponentProps } from "react";
import { Button } from "../atoms/Button";

/** Tombol aksi (varian & ukuran shadcn). Contoh: <ActionButton variant="outline" onClick={…}>Batal</ActionButton> */
export function ActionButton(props: ComponentProps<typeof Button>) {
  return <Button {...props} />;
}
