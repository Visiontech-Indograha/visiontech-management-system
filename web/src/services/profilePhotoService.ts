import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import { useSession } from "@/stores/sessionStore";
import { oversize, uploadFiles } from "@/services/uploadService";

/** PUT /employees/me/photo — `fileId` hasil unggah milik sendiri; `null` menghapus foto. */
export async function setMyPhoto(fileId: string | null): Promise<string | null> {
  return (await api.put<{ photo_file_id: string | null }>("/employees/me/photo", { file_id: fileId })).data
    .photo_file_id;
}

/** Unggah gambar lalu jadikan foto profil sendiri; menyegarkan `me` agar sidebar/akun langsung berubah. */
export function useChangeMyPhoto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File | null) => {
      if (file === null) return setMyPhoto(null);
      if (!file.type.startsWith("image/")) throw new Error("Pilih berkas gambar (JPG atau PNG).");
      const tooBig = oversize([file]);
      if (tooBig) throw new Error(tooBig);
      const [id] = await uploadFiles([file]);
      return setMyPhoto(id);
    },
    onSuccess: async () => {
      await useSession.getState().refreshMe();
      await qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}
