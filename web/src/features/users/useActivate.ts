import toast from "react-hot-toast";
import { ApiError } from "@/lib/api";
import type { UserOut } from "@/lib/types";
import { useActivateUser } from "./api";

/** Aktifkan kembali user nonaktif (FR-USR-06) dengan toast hasil. */
export function useActivate() {
  const activate = useActivateUser();
  return async (user: UserOut) => {
    try {
      await activate.mutateAsync(user.id);
      toast.success("Akun diaktifkan kembali.");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Terjadi kesalahan. Coba lagi.");
    }
  };
}
