import { api } from "@/lib/apiClient";

/** POST /face/enroll — daftarkan wajah sendiri dari 3–5 foto (sudut berbeda). */
export async function enrollFace(form: FormData): Promise<void> {
  await api.post("/face/enroll", form);
}
